# GeoClean — TODO / Open Issues

## 🔴 CRITICAL — Verify After Restart
- [ ] **maketrans bug fix** — The `str.maketrans` length mismatch in `country_resolver.py` was fixed in code and confirmed working from command line. User needs to do a FULL restart (kill all Python processes, relaunch streamlit, open fresh browser tab) to pick up the fix. If still failing after restart, investigate if there's a `.pyc` cache issue — delete `__pycache__` folders.
- [ ] **Street vs Location Name priority** — Fixed in `app.py` `prepare_row()`. When both are mapped, Street is now used for geocoding. Verify with Peru test file.
- [ ] **Existing lat/lon passthrough** — Verify that rows with existing coordinates in the upload show those values in the export.

## 🟡 In Progress
- [ ] UI overhaul to match OptiFlow styling (light theme, red header, green buttons, map view)
- [ ] Before/After map visualization

## 🟢 Completed This Session
- [x] PTV Developer Geocoding integration
- [x] Country-constrained search (countryFilter)
- [x] Comprehensive country resolver (200+ variants)
- [x] Result caching
- [x] Parallel processing (10 threads)
- [x] Address pre-cleaning & smart retry
- [x] PTV Places API for business names
- [x] OptiFlow-ready export format
- [x] Required fields prompt (service time, volume, timewindows)
- [x] Original data passthrough to export
- [x] Column detection improvements
- [x] Needs Review filter fix
- [x] GitHub repo + Streamlit Cloud deployment
- [x] Workspace reorganization
