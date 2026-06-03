# Implementation Plan: Reverse Geocode from Lat/Long

## Overview

This plan implements a third geocoding path (Path 0/decompose mode) in GeoClean. When uploaded data contains valid lat/lon coordinates alongside a single combined address column (with no separate street, city, state, or postal code columns mapped), the system uses reverse geocoding to decompose the combined address into structured components. The implementation touches `column_detector.py` (new detection function), a new `address_decomposer.py` module, and the orchestration logic in `app.py`.

## Tasks

- [x] 1. Enhance Column Detector with Single_Cell_Condition detection
  - [x] 1.1 Add `is_single_cell_condition(mapping, df)` function to `modules/column_detector.py`
    - Implement logic to check: lat/lon mapped with valid values, address mapped with non-empty values, no separate street/city/state/postal_code mapped
    - Return True only when all conditions are met
    - Handle edge case: mapped columns set to "(none)" or empty string treated as unmapped
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [x] 1.2 Update `get_mode(detected)` in `modules/column_detector.py` to return `"decompose"` mode
    - Add `"decompose"` as the highest-priority mode when `is_single_cell_condition` returns True
    - Preserve existing `"verify"`, `"geocode"`, and `"insufficient"` modes
    - _Requirements: 1.1, 1.2_

  - [x]* 1.3 Write property test for Single_Cell_Condition detection
    - **Property 1: Single_Cell_Condition Detection**
    - **Validates: Requirements 1.1, 1.2, 1.4, 1.5**

  - [x]* 1.4 Write unit tests for column detector enhancements
    - Test known file layouts (Peru logistics data with lat/lon + combined address → True)
    - Test structured address present → returns False
    - Test empty address column → returns False
    - Test mode priority (decompose > verify > geocode > insufficient)
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 2. Implement coordinate validation in Address Decomposer
  - [x] 2.1 Create `modules/address_decomposer.py` with `validate_coordinate(lat, lon)` function
    - Validate lat in [-90, 90], lon in [-180, 180]
    - Reject (0.0, 0.0) as invalid
    - Reject non-numeric, NaN, None, empty string values
    - Return `(is_valid: bool, reason: str)` tuple
    - _Requirements: 4.1, 4.2, 4.3_

  - [x]* 2.2 Write property test for coordinate validation
    - **Property 4: Coordinate Validation**
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [x] 3. Implement decompose result builder
  - [x] 3.1 Implement `_build_decompose_result(prep, reverse_result, source)` in `modules/address_decomposer.py`
    - Map PTV/Azure response fields to standard GeoClean result dict
    - Populate street (street + houseNumber), city, state, postal_code, country_code from API response
    - Leave fields as empty string when API response field is absent (never None or placeholder)
    - Preserve original coordinates as-is (not snapped)
    - Set `geocoding_source` to `"Reverse Geocode (Lat/Long)"`
    - Set `output_strategy` to `"decomposed_address"`
    - Preserve `original_address` from input combined address
    - Handle confidence scoring: use API quality score or default 0.5
    - _Requirements: 2.2, 2.3, 3.2, 5.3, 5.4, 7.1, 7.2, 7.3, 7.4_

  - [x]* 3.2 Write property test for reverse geocode response mapping
    - **Property 2: Reverse Geocode Response Mapping**
    - **Validates: Requirements 2.2, 2.3**

  - [x]* 3.3 Write property test for original address preservation
    - **Property 7: Original Address Preservation**
    - **Validates: Requirements 3.2, 7.1**

  - [x]* 3.4 Write property test for output format completeness
    - **Property 6: Output Format Completeness**
    - **Validates: Requirements 5.3, 5.4, 7.2**

  - [x]* 3.5 Write property test for confidence score bounds and defaults
    - **Property 8: Confidence Score Bounds and Defaults**
    - **Validates: Requirements 7.3, 7.4**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement batch decompose orchestration
  - [x] 5.1 Implement `decompose_batch(prepared_rows, progress_callback)` in `modules/address_decomposer.py`
    - Validate coordinates for each row using `validate_coordinate`
    - Call `reverse_geocode_batch_ptv` for valid coordinates (batch_size=500, max_concurrent=4)
    - For PTV failures, retry individually up to 2 attempts then try Azure Maps `reverse_geocode()`
    - Build result dicts via `_build_decompose_result` for successful responses
    - Return `(results, fallback_rows)` tuple: results list (None for failed) and fallback indices
    - Handle invalid coords + empty address: set confidence=0, needs_review=True
    - Invoke progress_callback(done, total) during processing
    - _Requirements: 2.1, 2.4, 3.1, 3.4, 4.4, 4.5, 5.1, 5.2, 6.1, 6.3, 6.4_

  - [x]* 5.2 Write property test for error handling preserves original address
    - **Property 3: Error Handling Preserves Original Address**
    - **Validates: Requirements 2.4**

  - [x]* 5.3 Write property test for invalid coordinates with empty address
    - **Property 5: Invalid Coordinates with Empty Address Produce Zero-Confidence Review**
    - **Validates: Requirements 4.4, 4.5**

  - [x]* 5.4 Write property test for partial batch failure retry limit
    - **Property 9: Partial Batch Failure Retry Limit**
    - **Validates: Requirements 6.3**

- [x] 6. Integrate decompose path into app.py orchestration
  - [x] 6.1 Add Single_Cell_Condition detection and UI notification in `app.py`
    - After column mapping is finalized, call `is_single_cell_condition(mapping, df)`
    - Display `st.info()` notification when decompose mode is detected
    - Display `st.warning()` when address column is mapped but contains no usable data
    - Update mode display in column mapping expander for `"decompose"` mode
    - _Requirements: 1.3, 1.4_

  - [x] 6.2 Add Path 0 (decompose) orchestration block in `app.py` geocoding section
    - Evaluate before existing Path 1/Path 2 split
    - Filter rows meeting Single_Cell_Condition with valid coordinates for decompose
    - Call `decompose_batch()` with progress callback wired to `st.progress()`
    - Display progress indicator showing rows processed / total qualifying rows
    - Route fallback rows into the existing forward geocode path (Path 2)
    - _Requirements: 2.1, 3.1, 3.3, 3.4, 5.1, 5.2, 6.1, 6.2, 6.4_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Integration testing and wiring
  - [x]* 8.1 Write integration tests for end-to-end decompose flow
    - Test: upload file with lat/lon + combined address → structured fields in output
    - Test: PTV failure → Azure fallback → valid output
    - Test: mixed file (some rows decompose, some forward geocode) → correct routing
    - Test: all invalid coords → entire file falls back to forward geocode
    - _Requirements: 2.1, 3.1, 3.4, 5.1, 5.2, 6.4_

  - [x]* 8.2 Write unit tests for decompose_batch orchestration
    - Test fallback chain: PTV fail → retry → Azure → forward geocode fallback
    - Test batch parameters (batch_size=500, max_concurrent=4)
    - Test progress callback invocation
    - _Requirements: 6.1, 6.3_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses Python with the existing project structure (Streamlit + modules/)
- PTV Developer API is the primary provider; Azure Maps is the fallback
- The existing `reverse_geocode_batch_ptv` and `reverse_geocode` (Azure) functions are reused

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "2.2"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "3.5"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "6.1"] },
    { "id": 6, "tasks": ["6.2"] },
    { "id": 7, "tasks": ["8.1", "8.2"] }
  ]
}
```
