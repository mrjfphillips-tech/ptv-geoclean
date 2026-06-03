# Requirements Document

## Introduction

This feature enables GeoClean to use existing latitude/longitude columns as the authoritative source for decomposing a combined (single-cell) address into structured address components via reverse geocoding. When the uploaded data contains lat/long values and the address exists only in a single combined column (without separate street, city, state, postal code fields), the system prioritizes the coordinates to populate individual address fields through reverse geocoding rather than attempting to parse or forward-geocode the combined address string.

## Glossary

- **GeoClean**: The Streamlit-based geocoding application that processes Excel/CSV files containing address data
- **Column_Detector**: The module responsible for identifying which columns in uploaded data correspond to address fields, coordinates, and other recognized fields
- **Reverse_Geocoder**: The module responsible for converting latitude/longitude coordinates into structured address components (street, number, city, state, postal code)
- **Address_Decomposer**: The logical component that orchestrates the detection of single-cell address + lat/long conditions and triggers reverse geocoding to fill structured fields
- **Combined_Address**: An address stored in a single spreadsheet cell containing the full address string (e.g., "123 Main St, Springfield, IL 62704") without separate columns for street, city, state, and postal code
- **Structured_Address_Fields**: The individual address components: street name, street number, city, state/province, and postal code stored in separate columns
- **Reverse_Geocoding**: The process of converting geographic coordinates (latitude, longitude) into a human-readable structured address
- **Single_Cell_Condition**: The state where address data exists only in one combined column and no separate street, city, state, or postal code columns are populated

## Requirements

### Requirement 1: Detect Single-Cell Address with Coordinates Condition

**User Story:** As a GeoClean user, I want the system to automatically detect when my data has lat/long columns alongside a single combined address column, so that it can choose the best geocoding strategy without manual intervention.

#### Acceptance Criteria

1. WHEN the uploaded data contains a mapped latitude column and a mapped longitude column AND the mapped address column contains at least one non-empty, non-NaN value AND no separate street, city, state, or postal code columns are mapped (i.e., all are unset or set to "(none)"), THE Column_Detector SHALL identify the data as meeting the Single_Cell_Condition.
2. WHEN the uploaded data contains latitude and longitude columns mapped but also has at least one separate street, city, state, or postal code column mapped with at least one non-empty, non-NaN value in that column, THE Column_Detector SHALL NOT identify the data as meeting the Single_Cell_Condition.
3. WHEN the Single_Cell_Condition is detected, THE GeoClean SHALL display an informational notification in the main content area indicating that reverse geocoding from coordinates will be used to decompose addresses.
4. IF the mapped address column is mapped but contains no non-empty values (all cells are empty, null, or NaN), THEN THE Column_Detector SHALL NOT identify the data as meeting the Single_Cell_Condition and THE GeoClean SHALL display a warning indicating that the address column contains no usable data.
5. WHEN a column is considered "mapped," THE Column_Detector SHALL define this as the column being either auto-detected by fuzzy matching or explicitly selected by the user in the column mapping dropdown and not set to "(none)".

### Requirement 2: Reverse Geocode Coordinates into Structured Address Fields

**User Story:** As a GeoClean user, I want the system to use my lat/long values to fill in street, number, city, state, and postal code, so that I get properly structured address data without manually splitting combined addresses.

#### Acceptance Criteria

1. WHEN the Single_Cell_Condition is met for a row and the latitude and longitude values are valid numeric coordinates, THE Reverse_Geocoder SHALL call the reverse geocoding API with those coordinates to retrieve structured address components.
2. WHEN the Reverse_Geocoder receives a successful API response (HTTP 200 with at least one result in the response body), THE Address_Decomposer SHALL populate the street name, street number, city, state, and postal code fields from the first (highest-ranked) result in the response.
3. WHEN the Reverse_Geocoder receives a successful API response that does not contain a particular address component (e.g., no street number), THE Address_Decomposer SHALL leave that field as an empty string rather than inserting a placeholder or guess.
4. IF the reverse geocoding API returns an error (non-2xx HTTP status), a timeout, or an empty result set for a given coordinate pair, THEN THE Address_Decomposer SHALL retain the original combined address value, set the row's needs_review flag to true, and record a descriptive message indicating the failure reason in the row's recommendation field.

### Requirement 3: Prioritize Coordinates Over Combined Address Parsing

**User Story:** As a GeoClean user, I want the lat/long coordinates to be treated as the source of truth over the combined address text, so that address decomposition is based on precise geographic data rather than text parsing heuristics.

#### Acceptance Criteria

1. WHEN the Single_Cell_Condition is met, THE GeoClean SHALL invoke reverse geocoding from the latitude and longitude values as the first and only method to obtain structured address fields, without invoking forward geocoding or text parsing from the combined address column.
2. WHEN reverse geocoding returns structured address fields for a row, THE Address_Decomposer SHALL populate the structured fields from the reverse-geocoded result and preserve the original combined address text in a dedicated reference column regardless of whether the values match.
3. WHEN reverse geocoding succeeds for a row under the Single_Cell_Condition, THE GeoClean SHALL NOT invoke forward geocoding or text parsing for that row.
4. IF reverse geocoding fails or returns no result for a row under the Single_Cell_Condition, THEN THE GeoClean SHALL fall back to forward geocoding from the combined address column and mark the row with a geocoding_source value indicating the fallback was used.

### Requirement 4: Validate Coordinate Values Before Reverse Geocoding

**User Story:** As a GeoClean user, I want invalid or missing coordinates to be handled gracefully, so that bad data in lat/long columns does not produce incorrect address results.

#### Acceptance Criteria

1. WHEN a latitude value is less than -90 or greater than 90, or a longitude value is less than -180 or greater than 180, THE Reverse_Geocoder SHALL skip reverse geocoding for that row, set the row's needs_review flag to true, and fall back to forward geocoding from the combined address column.
2. WHEN a latitude or longitude cell is empty, contains non-numeric text, or contains NaN, THE Reverse_Geocoder SHALL skip reverse geocoding for that row and fall back to forward geocoding from the combined address column.
3. WHEN both latitude and longitude values equal exactly zero, THE Reverse_Geocoder SHALL treat the coordinate pair as invalid, skip reverse geocoding for that row, and fall back to forward geocoding from the combined address column.
4. IF the Reverse_Geocoder skips reverse geocoding for a row due to invalid or missing coordinates AND the combined address column for that row is also empty, THEN THE Reverse_Geocoder SHALL set the row's needs_review flag to true and produce a result with a confidence score of 0.
5. WHEN the Reverse_Geocoder skips reverse geocoding due to coordinate validation failure, THE Reverse_Geocoder SHALL record the validation failure reason in the row's recommendation field.

### Requirement 5: Integrate with Existing Geocoding Pipeline

**User Story:** As a GeoClean user, I want reverse geocoding from lat/long to work seamlessly with the existing PTV and Azure Maps pipeline, so that I get consistent output regardless of which geocoding path is used.

#### Acceptance Criteria

1. THE Reverse_Geocoder SHALL use the PTV Developer API as the primary reverse geocoding provider when a PTV API key is configured.
2. WHEN the PTV Developer API is unavailable or returns no result, THE Reverse_Geocoder SHALL fall back to Azure Maps reverse geocoding.
3. THE Address_Decomposer SHALL produce output rows in the same format and with the same fields as forward-geocoded rows, including confidence score, geocoding source, and verification status.
4. WHEN reverse geocoding is used, THE GeoClean SHALL set the geocoding_source field to "Reverse Geocode (Lat/Long)" to distinguish it from forward geocoding results.

### Requirement 6: Support Batch Processing of Reverse Geocoding

**User Story:** As a GeoClean user, I want reverse geocoding to process all qualifying rows efficiently in batches, so that large files are handled with acceptable performance.

#### Acceptance Criteria

1. WHEN multiple rows meet the Single_Cell_Condition, THE Reverse_Geocoder SHALL process them using the existing PTV batch reverse geocoding mechanism with a default batch size of 500 positions per job and a maximum of 4 concurrent batch jobs.
2. WHILE batch reverse geocoding is in progress, THE GeoClean SHALL display a progress indicator showing the number of rows processed out of the total qualifying rows.
3. IF a batch reverse geocoding request partially fails (some positions return no result while the batch job itself succeeds), THEN THE Reverse_Geocoder SHALL retry each failed row individually up to a maximum of 2 retry attempts before marking unresolved rows for review.
4. IF all positions in a batch reverse geocoding request fail or the batch job itself cannot be submitted, THEN THE Reverse_Geocoder SHALL fall back to forward geocoding from the combined address column for the affected rows.

### Requirement 7: Preserve Original Data and Provide Traceability

**User Story:** As a GeoClean user, I want to see both the original combined address and the reverse-geocoded components in my output, so that I can verify the decomposition results.

#### Acceptance Criteria

1. THE Address_Decomposer SHALL preserve the original combined address value in a dedicated output column that remains unmodified, alongside the reverse-geocoded structured fields (street name, street number, city, state, postal code).
2. WHEN the output is exported, THE GeoClean SHALL include a geocoding_source column for each row containing a value that distinguishes reverse geocoding from coordinates (e.g., "Reverse Geocode (Lat/Long)") from forward geocoding results (e.g., "PTV", "Azure Maps").
3. THE GeoClean SHALL include the confidence score as a numeric value ranging from 0.0 to 1.0 in the output for each reverse-geocoded row, representing the geocoding API response quality.
4. IF the reverse geocoding API response does not include a confidence score, THEN THE GeoClean SHALL assign a default confidence score of 0.5 and set the confidence_level to "Medium" for that row.
