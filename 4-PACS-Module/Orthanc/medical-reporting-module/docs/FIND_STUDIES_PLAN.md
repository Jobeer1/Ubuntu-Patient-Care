## Find Studies — Implementation Plan

Brief: This document contains a concrete, step-by-step plan to build a robust, doctor-friendly Find Studies page that integrates with Orthanc (QIDO/WADO), provides a configurable DICOM viewer, and meets POPIA/privacy requirements.

Keep this checklist visible and mark items off as you complete them.

### Checklist (high level)
- [x] Backend: QIDO/WADO proxy endpoints (`/api/dicom/qido`, `/api/dicom/metadata`, `/api/dicom/wado`, `/api/dicom/thumbnail`).
- [x] Frontend: responsive Find Studies page with search, results, series browser.
- [ ] Viewer: embeddable DICOM viewer with grid manager, drag/drop series, resizable panes.
- [ ] Tools: window/level, cine, stack scrolling, measurements, snapshot export.
- [ ] Layout presets: save/load user presets (localStorage + server optional).
- [ ] Security: server-side proxying, session auth, audit logging, encrypted cache (POPIA).
- [ ] Tests: unit + integration + e2e (Playwright/Selenium).

---

## 1. Goals & acceptance criteria

- Doctors can search Orthanc for studies and view them in a flexible viewer.
- Viewer supports configurable grid (1,2,3,4,6, custom), drag/drop series into slots, resizable panes.
- Viewer includes window/level, zoom, pan, cine, stack scroll, measurement tools, and snapshot export.
- All DICOM requests go through the server (proxy), and user sessions are validated.
- Performance: lazy-load instances, cache thumbnails, stream large images.
- Accessibility and South African-friendly UI (colors, font sizes, clear labels).

Acceptance tests (done when):
- Search returns Orthanc results (or demo sample) and shows metadata.
- User can open a study and drag two series into two viewports and perform window/level adjustments.
- Exported snapshot is downloadable and recorded in audit logs.

---

## 2. Architecture & Data Contracts

Backend responsibilities:
- Proxy Orthanc QIDO and WADO calls:
  - `GET /api/dicom/qido?q=<term>&limit=50` → returns array of studies.
  - `GET /api/dicom/metadata/<studyId>` → returns study + series + instance metadata.
  - `GET /api/dicom/wado/<studyId>/<seriesId>/<instanceId>` → proxied WADO-RS image (streamed).
  - `GET /api/dicom/thumbnail/<studyId>/<seriesId>/<instanceId>` → small preview image (cache).
- Validate session/auth for all endpoints and log accesses.

Frontend data shapes (JSON):
- Study: { studyInstanceUid, patientName, patientId, studyDate, modalitiesInStudy, seriesCount }
- Series: { seriesInstanceUid, seriesNumber, modality, instanceCount, thumbnailUrl }
- Instance: { sopInstanceUid, rows, cols, wadoUrl, thumbnailUrl }

---

## 3. Viewer choice & integration options

Option A — OHIF Viewer (recommended if adding React is acceptable):
- Pros: feature-complete (MPR, measurements, layout management), fast to deploy.
- Integration: run OHIF as an embedded app (iframe) or mount a small React bundle in `/viewer` route. Use server proxy endpoints for QIDO/WADO.

Option B — Cornerstone.js (vanilla JS):
- Pros: Works with existing vanilla stack, full control.
- Cons: Requires building higher-level features (MPR, layout manager) manually.

Recommendation: If project can add a small React bundle, embed OHIF; otherwise use Cornerstone for incremental builds.

---

## 4. Step-by-step implementation (Sprint-level tasks)

Sprint 1 (Days 0–3) — Basic search and single viewport ✅ COMPLETED
1. ✅ Add backend proxy endpoints (create `api/dicom_api.py`): implement QIDO and metadata endpoints using requests to ORTHANC_URL (config in `config/settings.py` as ORTHANC_URL, ORTHANC_AUTH).
2. ✅ Add `templates/find_studies.html` (already added) and a new frontend file `frontend/static/js/find-studies.js` to call `/api/dicom/qido` and show results.
3. ✅ Implement a single Cornerstone/preview image viewport that can load one instance via `GET /api/dicom/wado/...`.
4. ✅ Acceptance: search → select study → viewer loads first instance.

**Testing Sprint 1:**
- Restart server: `py app.py`
- Visit: https://127.0.0.1:5443/find-studies
- Expected: auto-search shows demo studies, click study opens modal viewer, click series shows images with prev/next
- Files added: `api/dicom_api.py` (extended), `config/settings.py`, `frontend/static/js/find-studies.js`

Sprint 2 (Days 3–8) — Grid manager, series browser, drag/drop ✅ COMPLETED
1. ✅ Implement LayoutManager component (CSS Grid + JS) supporting common grids (1x1,2x1,1x2,2x2,3x2,2x3).
2. ✅ Build series browser UI listing series thumbnails; make series items draggable.
3. ✅ Implement drop handler in viewport that loads a series as a stack with instance navigation.
4. ✅ Save presets to `localStorage` and provide layout management (save/load presets).
5. ✅ Acceptance: user configures 2x2, drags series into viewports, instances are scrollable with controls.

**Testing Sprint 2:**
- Visit: https://127.0.0.1:5443/find-studies
- Search and open study viewer
- Expected: layout selector (1x1, 2x1, 2x2, etc.), draggable series in left panel, drop zones in grid
- Expected: drag series to viewport slots, see images with navigation controls (prev/next, clear)
- Expected: save/load presets functionality with localStorage persistence
- Files modified: `frontend/static/js/find-studies.js` (enhanced with grid manager, drag/drop, presets)

Sprint 3 (Days 8–14) — Tools, sync, export
1. Add window/level, pan/zoom, cine playback, stack scroll tools (Cornerstone Tools or OHIF plugins).
2. Implement measurement tools and snapshot export (canvas to PNG) and save to server if desired.
3. Add sync-scroll toggle across viewports.
4. Acceptance: doctor can measure and export snapshots.

Sprint 4 (Days 14–18) — Performance, security, tests
1. Add caching for thumbnails and optional disk cache for WADO streaming under `instance/dicom_cache` (store TTL and encrypt if required).
2. Add audit logging for study access and exports.
3. Write unit tests for backend endpoints (mock Orthanc), write Playwright e2e tests for search → open → measure → export.
4. Accessibility pass and visual polish (SA color palette, font sizes).

---

## 5. Implementation details & code pointers

Backend sample responsibilities (to implement in `api/dicom_api.py`):
- Use `requests` with timeout to call Orthanc QIDO endpoint:
  - requests.get(f"{ORTHANC_URL}/tools/find", auth=..., params={...}) OR QIDO-RS endpoint
- Stream WADO responses directly to client using Flask `Response` with `stream_with_context`.

Frontend pointers:
- Create `frontend/static/js/find-studies.js` and register it in `templates/find_studies.html`.
- If using Cornerstone: include cornerstone, cornerstoneWADOImageLoader, dicomParser, cornerstoneTools via CDN or local copies in `frontend/static/vendor/`.

Files to add/modify
- `api/dicom_api.py` — new backend routes for QIDO/WADO/thumbnail.
- `templates/find_studies.html` — already present; extend with viewer mount points and include `find-studies.js`.
- `frontend/static/js/find-studies.js` — new frontend logic.
- `frontend/static/vendor/*` — optional viewer libs (Cornerstone or OHIF bundle).
- `config/settings.py` — add ORTHANC_URL, ORTHANC_AUTH (read from env vars).

---

## 6. Security and POPIA checklist

- Proxy Orthanc server-side to avoid exposing credentials or CORS to browser.
- Validate session for all API endpoints; reuse existing auth middleware.
- Redact PHI where possible in logs; keep audit log entries (user, time, studyId, action).
- Cache with TTL and encrypt cache files using existing secure storage pattern.

---

## 7. Testing plan

- Unit tests (backend): mock Orthanc responses using `responses` or `requests-mock` and validate JSON translation.
- Frontend unit/component tests: small tests for layout manager and drag/drop logic (Jest or simple DOM tests).
- E2E: Playwright test script: search → open study → load 2 series into 2 viewports → perform window/level → export PNG.

---

## 8. Acceptance criteria & sign-off

Mark the feature done when all acceptance tests pass and a short user walkthrough (video or test steps) demonstrates:
- Searching and opening multiple studies from Orthanc.
- Configuring a 2x2 comparison and loading series by drag/drop.
- Performing window/level and measurement; exporting snapshot and verifying audit log entry.

---

## 9. Optional enhancements (after MVP)

- MPR (multi-planar reconstructions) support for CT/MR (OHIF recommended).
- Shared collaboration: link two viewports for synchronized annotations.
- Preset templates for common layouts used by radiologists (e.g., chest AP + lateral).

---

## 10. Next immediate task I can implement for you

Choose one and I will open a PR:
- A: Implement `api/dicom_api.py` with safe QIDO proxy and a working `/api/dicom/qido` endpoint (required before the frontend).
- B: Implement `frontend/static/js/find-studies.js` and wire it to the current `templates/find_studies.html` to show real search results using a demo dataset.
- C: Integrate OHIF as an iframe and demonstrate loading a sample study via server proxy.

Please reply with A, B or C and I will start implementing that next.
