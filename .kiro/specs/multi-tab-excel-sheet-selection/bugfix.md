# Bugfix Requirements Document

## Introduction

When a user uploads a multi-sheet Excel file (.xlsx/.xls) in the GeoClean Streamlit app, the application silently reads only the first sheet without offering the user a choice. If the order/address data resides on a different sheet, the app either processes incorrect data or shows no usable rows. The fix must detect multi-sheet workbooks and prompt the user to select the correct sheet before processing continues.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN an Excel file with multiple sheets is uploaded THEN the system silently reads only the first sheet without informing the user or offering a choice
1.2 WHEN the order data resides on a sheet other than the first THEN the system processes incorrect data (wrong columns/rows) or shows zero usable address rows
1.3 WHEN an Excel file with multiple sheets is uploaded THEN the system provides no indication that additional sheets exist in the workbook

### Expected Behavior (Correct)

2.1 WHEN an Excel file with multiple sheets is uploaded THEN the system SHALL detect all available sheet names and present a selection widget (e.g., dropdown/selectbox) for the user to choose which sheet to load
2.2 WHEN the user selects a sheet from the widget THEN the system SHALL read and process only the selected sheet's data
2.3 WHEN an Excel file with multiple sheets is uploaded THEN the system SHALL display the number of sheets found so the user is aware the workbook contains multiple tabs

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a single-sheet Excel file is uploaded THEN the system SHALL CONTINUE TO read that sheet directly without showing a sheet selection widget
3.2 WHEN a CSV file is uploaded THEN the system SHALL CONTINUE TO read it directly without any sheet selection logic
3.3 WHEN an Excel file is uploaded and a sheet is selected THEN the system SHALL CONTINUE TO perform column auto-detection, data preview, and geocoding exactly as before
