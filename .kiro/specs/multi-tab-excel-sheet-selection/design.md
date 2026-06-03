# Multi-Tab Excel Sheet Selection Bugfix Design

## Overview

When users upload multi-sheet Excel files (.xlsx/.xls), the GeoClean app silently reads only the first sheet via `pd.read_excel(uploaded_file)` without the `sheet_name` parameter. This causes incorrect data processing or empty results when address data lives on a non-first sheet. The fix intercepts Excel uploads, inspects available sheet names using `pd.ExcelFile`, and—when multiple sheets exist—renders a Streamlit `st.selectbox` so the user can choose the correct sheet before the DataFrame is loaded.

## Glossary

- **Bug_Condition (C)**: The uploaded file is an Excel workbook (.xlsx/.xls) containing more than one sheet, and the system reads it without offering sheet selection
- **Property (P)**: When C holds, the system presents a sheet selection widget and reads only the user-chosen sheet
- **Preservation**: Single-sheet Excel files and CSV files continue to load immediately without any additional UI; all downstream processing (column detection, preview, geocoding) remains unchanged
- **`pd.ExcelFile`**: Pandas class that parses an Excel workbook's metadata (including sheet names) without reading full cell data
- **`st.selectbox`**: Streamlit widget that renders a dropdown selector and returns the user's choice

## Bug Details

### Bug Condition

The bug manifests when a user uploads an Excel file that contains two or more sheets. The `pd.read_excel(uploaded_file)` call defaults to `sheet_name=0`, silently reading only the first sheet. The user is never informed that additional sheets exist and cannot direct the app to read a different sheet.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type UploadedFile
  OUTPUT: boolean

  RETURN input.name ENDS_WITH ('.xlsx' OR '.xls')
         AND numberOfSheets(input) > 1
         AND systemReadsWithoutSheetSelection(input)
END FUNCTION
```

### Examples

- **Example 1**: User uploads `orders.xlsx` with sheets ["Summary", "Orders", "Returns"]. App reads "Summary" (first sheet) which contains pivot tables, not address rows. Result: 0 usable rows, no geocoding possible.
- **Example 2**: User uploads `logistics_data.xlsx` with sheets ["Metadata", "Addresses"]. App reads "Metadata" which has config parameters. Result: column auto-detection fails or maps to wrong fields.
- **Example 3**: User uploads `report.xlsx` with sheets ["Sheet1", "Sheet2"]. "Sheet1" has the data the user wants. App reads it correctly by luck, but user is never informed "Sheet2" exists.
- **Edge Case**: User uploads `single.xlsx` with one sheet ["Data"]. App reads it directly—no bug, no widget needed.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Single-sheet Excel files load immediately without any sheet selection UI
- CSV files bypass all Excel sheet logic entirely
- After a sheet is selected (or auto-selected for single-sheet files), column auto-detection, data preview, mapping overrides, and geocoding run exactly as before
- Sidebar column mapping settings remain functional and unaffected
- Template download button continues to work

**Scope:**
All inputs that do NOT involve multi-sheet Excel files should be completely unaffected by this fix. This includes:
- CSV file uploads (`.csv`)
- Single-sheet Excel file uploads (`.xlsx`/`.xls` with exactly one sheet)
- All downstream processing after the DataFrame is loaded (column detection, geocoding, export)

## Hypothesized Root Cause

Based on the bug description, the most likely issue is:

1. **Missing Sheet Enumeration**: The code calls `pd.read_excel(uploaded_file)` without first checking how many sheets exist. The `sheet_name` parameter defaults to `0` (first sheet).

2. **No Conditional UI Branch**: There is no logic to branch between single-sheet (direct load) and multi-sheet (prompt user) paths. The file reading block is a simple if/else on file extension only.

3. **No Use of `pd.ExcelFile`**: The `pd.ExcelFile` class (which exposes `.sheet_names`) is never instantiated, so the app has no way to discover available sheets without reading cell data.

4. **Streamlit Session State Not Leveraged**: Even if sheet names were detected, there is no session state key to persist the user's sheet selection across Streamlit reruns.

## Correctness Properties

Property 1: Bug Condition - Multi-Sheet Excel Presents Sheet Selector

_For any_ uploaded Excel file where the number of sheets is greater than 1 (isBugCondition returns true), the fixed code SHALL detect all sheet names, display the count of sheets to the user, and present a selectbox widget allowing the user to choose which sheet to load. The DataFrame SHALL be read from the user-selected sheet only.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Single-Sheet and CSV Bypass

_For any_ uploaded file where the bug condition does NOT hold (single-sheet Excel or CSV), the fixed code SHALL produce the same behavior as the original code—loading the file directly without presenting a sheet selection widget, preserving the existing immediate-load experience.

**Validates: Requirements 3.1, 3.2, 3.3**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `app.py`

**Section**: File upload handling block (around line 125–130)

**Specific Changes**:

1. **Detect Sheet Count**: After confirming the file is Excel (not CSV), instantiate `pd.ExcelFile(uploaded_file)` and read `.sheet_names`.

2. **Branch on Sheet Count**:
   - If `len(sheet_names) == 1`: read directly with `pd.read_excel(uploaded_file)` (current behavior preserved).
   - If `len(sheet_names) > 1`: display an info message with sheet count, render `st.selectbox` with sheet names, then read with `pd.read_excel(uploaded_file, sheet_name=selected_sheet)`.

3. **Display Sheet Count**: Use `st.info(f"📑 Found {len(sheet_names)} sheets in workbook")` to satisfy requirement 2.3.

4. **Reset File Pointer**: After `pd.ExcelFile` reads the file, call `uploaded_file.seek(0)` before `pd.read_excel` to ensure the file buffer is at the start.

5. **Handle Streamlit Rerun**: The `st.selectbox` widget inherently persists selection across reruns via Streamlit's widget state—no extra session state management needed for the basic case.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that mock a multi-sheet Excel upload and verify whether the current code presents a sheet selector or silently reads the first sheet. Run on UNFIXED code to observe failures.

**Test Cases**:
1. **Multi-Sheet No Widget Test**: Upload a 3-sheet Excel file → verify no selectbox is rendered (will pass on unfixed code, confirming the bug)
2. **Wrong Sheet Data Test**: Upload a 2-sheet file where sheet 2 has address data → verify the app reads sheet 1 instead (will demonstrate incorrect data on unfixed code)
3. **No Sheet Count Display Test**: Upload a multi-sheet file → verify no info message about sheet count appears (confirms bug condition 1.3)
4. **Single-Sheet Baseline Test**: Upload a single-sheet file → verify it loads correctly (should pass on unfixed code—baseline)

**Expected Counterexamples**:
- Multi-sheet files always produce a DataFrame from sheet index 0
- No Streamlit selectbox or info widget is rendered for sheet selection
- Possible cause: `pd.read_excel` called without `sheet_name` parameter and no prior sheet enumeration

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := load_excel_fixed(input)
  ASSERT sheetSelectorDisplayed(result)
  ASSERT sheetCountMessageShown(result)
  ASSERT dataFrameReadFromSelectedSheet(result)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT load_excel_original(input) = load_excel_fixed(input)
  ASSERT noSheetSelectorDisplayed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (various single-sheet Excel files, CSVs with different column sets)
- It catches edge cases that manual unit tests might miss (empty files, files with special characters in names)
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for single-sheet Excel and CSV uploads, then write property-based tests capturing that behavior continues unchanged after the fix.

**Test Cases**:
1. **CSV Direct Load Preservation**: Verify CSV files load without any sheet selection logic before and after fix
2. **Single-Sheet Excel Preservation**: Verify single-sheet Excel files load directly without a selectbox before and after fix
3. **Downstream Processing Preservation**: Verify column auto-detection and data preview work identically after sheet selection completes
4. **File Type Detection Preservation**: Verify `.csv` vs `.xlsx`/`.xls` branching remains correct

### Unit Tests

- Test that `pd.ExcelFile` correctly identifies sheet names for multi-sheet workbooks
- Test that `st.selectbox` is rendered only when sheet count > 1
- Test that `pd.read_excel` receives the correct `sheet_name` parameter
- Test that `uploaded_file.seek(0)` is called between ExcelFile inspection and read_excel
- Test edge case: Excel file with exactly 1 sheet skips widget

### Property-Based Tests

- Generate random DataFrames with varying column counts and row counts, write to multi-sheet Excel, verify sheet selector appears and correct sheet is read
- Generate random single-sheet Excel files, verify no selector appears and data loads identically to original code
- Generate random CSV data, verify sheet logic is completely bypassed

### Integration Tests

- End-to-end test: upload multi-sheet file → select sheet → verify column detection runs on correct data
- End-to-end test: upload single-sheet file → verify immediate load → verify geocoding pipeline works
- End-to-end test: upload CSV → verify no sheet logic → verify full pipeline works
