# Implementation Plan

## Overview

This task list implements the bugfix for multi-tab Excel sheet selection. The GeoClean app currently reads only the first sheet of multi-sheet Excel files without offering the user a choice. The fix detects multi-sheet workbooks and presents a sheet selection widget before processing.

## Tasks

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Multi-Sheet Excel Silently Reads First Sheet
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to concrete failing cases: any Excel file with >1 sheet uploaded to the app
  - Create a test file `tests/test_sheet_selection.py` using `pytest` and `hypothesis` (or `pytest` with parameterized cases)
  - Mock `st.file_uploader` to return a multi-sheet Excel BytesIO (e.g., 3 sheets: ["Summary", "Orders", "Returns"])
  - Generate multi-sheet Excel workbooks using `openpyxl` with varying sheet counts (2-5 sheets) and random DataFrame content per sheet
  - Property assertion: for all multi-sheet Excel inputs where `isBugCondition(input)` is true (file ends with .xlsx/.xls AND numberOfSheets > 1), the system SHOULD call `st.selectbox` with the list of sheet names and display an info message with the sheet count
  - On UNFIXED code: `pd.read_excel(uploaded_file)` is called without `sheet_name` parameter, no `st.selectbox` is rendered, no sheet count info is displayed
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found (e.g., "3-sheet workbook uploaded → no selectbox rendered, pd.read_excel called with default sheet_name=0, sheet count info never displayed")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Single-Sheet Excel and CSV Direct Load
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: Upload a single-sheet Excel file on UNFIXED code → no selectbox rendered, DataFrame loaded directly via `pd.read_excel(uploaded_file)`
  - Observe: Upload a CSV file on UNFIXED code → no sheet logic triggered, DataFrame loaded via `pd.read_csv(uploaded_file)`
  - Observe: After DataFrame is loaded, column auto-detection (`detect_columns`) runs identically regardless of file source
  - Write property-based test using `hypothesis`: for all single-sheet Excel files (generated with random DataFrames of 1-50 columns, 1-100 rows), verify:
    - No `st.selectbox` for sheet selection is rendered
    - `pd.read_excel` is called without explicit `sheet_name` or with `sheet_name=0` (same default behavior)
    - The loaded DataFrame matches the content written to the single sheet
  - Write property-based test: for all CSV files (generated with random DataFrames), verify:
    - No sheet enumeration logic is triggered (`pd.ExcelFile` is never called)
    - `pd.read_csv` is called directly
    - The loaded DataFrame matches the CSV content
  - Write property-based test: for all files (CSV or single-sheet Excel), verify column detection output is identical before and after fix
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 3. Fix for multi-sheet Excel files silently reading only first sheet

  - [ ] 3.1 Implement the fix in `app.py`
    - In the file upload handling block (around line 125-130), after confirming the file is Excel (not CSV):
    - Instantiate `pd.ExcelFile(uploaded_file)` and read `.sheet_names`
    - Call `uploaded_file.seek(0)` to reset the file pointer after ExcelFile inspection
    - Add conditional branch on `len(sheet_names)`:
      - If `len(sheet_names) == 1`: read with `pd.read_excel(uploaded_file)` (preserves current behavior)
      - If `len(sheet_names) > 1`: display `st.info(f"📑 Found {len(sheet_names)} sheets in workbook")`, render `st.selectbox("Select sheet", sheet_names)`, then read with `pd.read_excel(uploaded_file, sheet_name=selected_sheet)`
    - Call `uploaded_file.seek(0)` again before `pd.read_excel` to ensure clean read after selectbox interaction
    - _Bug_Condition: isBugCondition(input) where input.name ends with .xlsx/.xls AND numberOfSheets(input) > 1 AND systemReadsWithoutSheetSelection(input)_
    - _Expected_Behavior: sheetSelectorDisplayed(result) AND sheetCountMessageShown(result) AND dataFrameReadFromSelectedSheet(result)_
    - _Preservation: Single-sheet Excel files load directly without selectbox; CSV files bypass all Excel sheet logic; downstream processing unchanged_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Multi-Sheet Excel Presents Sheet Selector
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior (selectbox rendered, sheet count shown, correct sheet read)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Single-Sheet Excel and CSV Direct Load
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix (no regressions introduced for single-sheet Excel or CSV uploads)

- [ ] 4. Checkpoint - Ensure all tests pass
  - Run full test suite: `pytest tests/test_sheet_selection.py -v`
  - Verify Property 1 (Bug Condition) test passes on fixed code
  - Verify Property 2 (Preservation) tests pass on fixed code
  - Verify no other existing tests are broken
  - Ensure all tests pass, ask the user if questions arise

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1", "2"],
      "description": "Write exploration and preservation tests before fix"
    },
    {
      "wave": 2,
      "tasks": ["3.1"],
      "description": "Implement the fix in app.py"
    },
    {
      "wave": 3,
      "tasks": ["3.2", "3.3"],
      "description": "Verify exploration and preservation tests pass after fix"
    },
    {
      "wave": 4,
      "tasks": ["4"],
      "description": "Final checkpoint - ensure all tests pass"
    }
  ]
}
```

## Notes

- Tests in tasks 1 and 2 must be written and run BEFORE the fix is implemented to establish baseline behavior
- The exploration test (task 1) is expected to FAIL on unfixed code — this confirms the bug exists
- The preservation tests (task 2) are expected to PASS on unfixed code — this captures behavior to protect
- After the fix, both test categories should PASS, confirming the bug is resolved without regressions
