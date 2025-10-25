## NAS Discovery & Device Management: Design and Implementation Plan

Purpose
-------
This document defines a precise, actionable plan to implement, harden, and test the NAS/network discovery features in the NASIntegration backend and matching frontend UX. It targets accuracy, maintainability, and a user-friendly UI, while preserving compatibility with existing endpoints used by the current UI.

Checklist (requirements to satisfy)
----------------------------------
- [ ] Fix startup/import error so `py app.py` runs (restore package import boundaries / compatibility)
- [ ] Ensure backend endpoints match frontend expectations and provide compatibility aliases (`/api/nas/ping_range`, `/api/nas/enhanced_discovery`, `/api/nas/scan_device`, `/api/nas/device_info/<ip>`, `/api/nas/rename-device` etc.)
- [ ] CIDR-aware range scanning: accept `networkRange` (CIDR) or `startIp`/`endIp` and derive host list server-side
- [ ] Ping-range: concurrent, bounded, ARP-aware fallback (use ARP cache if ICMP fails)
- [ ] Enhanced discovery: optional port-scan (opt-in), banner checks, and `nas_confidence_score` (0–100)
- [ ] Persist local friendly names in `device_names.json` and serve them with device lists
- [ ] Per-IP actions: ping, port-scan (opt-in), rename; present consistent JSON shapes for UI
- [ ] Defensive frontend parsing & UI: handle non-JSON server responses, show cached devices on load, show progressive/streamed results for large scans
- [ ] Tests: unit tests for scoring, ping-range logic (ARP fallback), and port-scan heuristics; integration smoke test for endpoints
- [ ] Quality gates: lint/typecheck, run unit tests, run a short scan smoke test locally

Contract: small concise API contracts
----------------------------------

1) POST /api/nas/ping_range
   - Input JSON: { "startIp": "10.0.0.1", "endIp": "10.0.0.254", "maxConcurrent": 64, "timeoutMs": 500 }
   - Output JSON: { "range": "10.0.0.1-10.0.0.254", "stats": {"scanned":254, "online":12}, "results": [{"ip":"10.0.0.5","status":"online|offline","response_ms":12|null,"mac":"aa:bb:cc:dd:ee:ff","via_arp":true|false}] }

2) POST /api/nas/enhanced_discovery
   - Input JSON: { "networkRange":"192.168.1.0/24", "include_port_scan": true }
   - Output JSON: same as ping_range plus optional `port_scan` block per device:
     "port_scan": {"open_ports": [21,22], "nas_confidence_score": 86, "evidence":["open:5000/tcp","banner:www/NAS-Vendor"] }

3) POST /api/nas/scan_device
   - Input JSON: { "ip":"10.0.0.5", "scan_ports": true }
   - Output JSON: { "ip":"10.0.0.5", "open_ports":[80,5000], "nas_confidence_score": 92, "banners":{5000:"NAS-HTTP/1.1"} }

4) POST /api/nas/rename-device
   - Input JSON: { "ip":"10.0.0.5", "name":"Ward-CT-1" }
   - Output JSON: { "ip":"10.0.0.5", "ok":true }

Data shapes and persistence
---------------------------
- `network_settings.json` — normalized keys: `startIp`, `endIp`, `networkRange`, `timeoutMs`, `maxConcurrent`
- `discovered_devices.json` — cache of last discovery results, list of device objects (ip, mac, manuf, local_name)
- `device_names.json` — map ip -> local_name (authoritative for user-supplied names)

Edge cases and decisions
------------------------
- Large CIDR (>/24): require explicit user confirmation in UI; server may limit to first N hosts (configurable). Default behavior: cap to 254 hosts and warn.
- ARP-only devices: when ping fails but ARP entry exists, mark `status: offline`? No — mark `status: online` with `response_ms: null` and `via_arp: true` and visible badge "ARP" so user knows it's derived.
- Non-JSON responses / HTML 404: backend should set correct `Content-Type: application/json` for API; frontend should not attempt JSON.parse on non-JSON responses and instead surface the text.
- Port scanning is opt-in and short-timeout only. Avoid heavy scanning to reduce IDS false positives. Respect `include_port_scan` flag.

Implementation tasks (phased)
---------------------------

Phase A — Stabilize and compatibility (1–2 days)
- Ensure `py app.py` works: fix relative import issues in `backend` package (make `__init__.py` if required) and restore any wrappers needed by other modules.
- Add compatibility aliases at `nas_core` to match both old and new endpoint names.
- Add defensive API helper on frontend (`makeAPIRequest`) to inspect Content-Type before parsing.
- Tests: basic smoke test that server starts and endpoints return JSON skeletons.

Phase B — Ping/ARP improvements (2–3 days)
- Implement server-side CIDR -> hosts expansion (use `ipaddress` stdlib). Add validation and limit checks.
- Rework `ping_range` to:
  - accept `networkRange` or `startIp`/`endIp`
  - build unique host list (exclude network and broadcast)
  - run concurrent pings with thread pool (bounded by `maxConcurrent`)
  - after ICMP failure, consult ARP cache and mark `via_arp` if present
  - produce `results` sorted by IP
- Tests: unit tests for CIDR expansion and ARP fallback logic.

Phase C — Enhanced discovery and scanning (3–4 days)
- Implement `scan_device` that:
  - optionally does a targeted TCP connect scan of prioritized NAS ports (21,22,80,443,5000,5001,8080,9000,5000-5010)
  - does quick banner grabs (HTTP title, server header) with short timeout
  - computes `nas_confidence_score` by weighted evidence: open known NAS port, banner contains vendor string, mac OUI matches known NAS vendor, response to admin URL
  - ensure scanning is opt-in and limited (per-host) and rate-limited
- Expose `nas_confidence_score` in `enhanced_discovery` responses
- Tests: unit tests for scoring and mock socket-based banner reads

 Phase D — UX wiring & persistence (1–2 days)
- Frontend: ensure `network-discovery.js`, `device-management.js` call corrected endpoints, show cached devices on load, show progress & per-host badges
- Persist `device_names.json` writes and read-through logic so UI always shows user-supplied names
- Add inline rename UI and confirmation for large scans
- Tests: small end-to-end smoke test script that runs `enhanced_discovery` against `127.0.0.1/32` or local network and verifies JSON shape

Progress delta (2025-08-18):

- ✅ Frontend scan result rendering fixed: `scanDevice()` now injects detailed scan HTML into `#discoveryResults` and appends an inline "Scanned: X open" note to the device row response cell.
- ✅ `formatScanResult()` updated to normalize backend shapes where `open_ports` may be numeric arrays (e.g., [22,445]) or object arrays and to display `nas_confidence_score` and `nas_confidence_reason` evidence when present.
- Note: Backend already computes `nas_confidence_score` in `backend/routes/nas_utils.py` and returns banners and services; frontend now displays these fields when included in `scan-device` responses.

Next UX tasks:

- Offer inline expansion (accordion) instead of replacing the discovery panel when rendering scan results (preferred UX improvement).
- Add a small visual spinner/loader while port scans run, and a dismissible scan result card.
- Add a unit/integration test that simulates `/api/nas/scan-device` responses with both numeric and object-shaped `open_ports` and verifies the frontend DOM contains the expected table entries.

Phase E — Quality, docs, and follow-ups (1–2 days)
- Add sample `fingerprints.json` starter file and document how to extend
- Add tests and CI job (if repo has CI) to run lint and the unit/integration tests
- Document runtime constraints (needs root for raw ICMP on some systems; fallback to system ping command or use `ping` subprocess on Windows)

Files to create/modify (concrete)
--------------------------------
- Modify: `backend/device_management.py` — split heavy functions to `network_discovery.py` and `nas_utils.py` if not already; keep thin compatibility wrappers in `device_management.py`.
- Create/modify: `backend/network_discovery.py` — CIDR expansion, ping_range, enhanced_discovery glue
- Create/modify: `backend/nas_utils.py` — port scanner, banner grabs, scoring, persistence helpers for `device_names.json`
- Modify: `backend/nas_core.py` — endpoints and compatibility aliases
- Modify: frontend `backend/static/js/network-discovery.js`, `backend/static/js/nas-core.js`, `backend/static/js/device-management.js`, `backend/static/js/ui-helpers.js` — defensive parsing, show cached devices and progress, per-IP actions
- Add: `backend/DISCOVERY_AND_NAS_PLAN.md` (this file)

Testing and quality gates
------------------------
- Local quick checks (on every change):
  1. `py app.py` starts without ImportError
  2. curl or browser GET `/api/nas/ping_range` returns JSON with correct headers
  3. Run unit tests: `pytest backend/tests/test_network_discovery.py -q`
- Unit/Integration tests to add:
  - CIDR expansion unit tests (ip address edge cases)
  - ARP fallback unit tests (simulate ARP read)
  - nas_confidence scoring tests with synthetic evidence
  - scan_device: mock socket connect tests
- Acceptance/smoke: small script `scripts/smoke_scan.py` that runs `enhanced_discovery` against `127.0.0.1/32` and asserts shape

Security & operational notes
----------------------------
- Port scanning: make it opt-in. Add explicit UI warning when user enables scanning or attempts scans beyond /24.
- Avoid long-lived raw sockets or high-frequency scanning to prevent IDS alerts. Default timeouts low (200–1000ms) and small port lists.
- Respect user privacy: do not log or transmit user-entered credentials. If Orthanc linking is implemented later, require explicit credential entry and store securely.

Deliverables and how I will verify
---------------------------------
- New/modified backend endpoints that start with `py app.py` and pass unit tests (PASS criteria: all unit tests added pass locally).
- Frontend changes: cached devices visible at load; per-IP ping shows green/red badges; rename persists to `device_names.json`.
- Verification steps I will run after implementation:
  1. Start server: `py app.py`
  2. Visit discovery UI and load cached devices
  3. Run `enhanced_discovery` for a single host (127.0.0.1) with `include_port_scan: false` and `true` and inspect returned JSON
  4. Run unit tests and lint

Next steps (what I will implement first)
--------------------------------------
1. Create or repair `backend/__init__.py` and ensure `py app.py` works (Phase A).  
2. Implement server-side CIDR -> hosts expansion and the robust `ping_range` with ARP fallback (Phase B).  
3. Wire the `include_port_scan` into `enhanced_discovery` and implement `scan_device` with scoring (Phase C).

Notes / assumptions
-------------------
- Assumed runtime is Python 3.8+ (for `ipaddress` convenience).  
- Assume repository already has `backend/static/js` UI assets and that minor frontend edits are acceptable.  
- If direct raw ICMP sockets require elevated privileges on the deployment environment, we will fall back to the platform `ping` command or use a small helper that wraps system ping.

Contact points for follow-ups
----------------------------
- I will open incremental PRs covering Phase A, then B, then C. Each PR will include unit tests and a short smoke test script.

---
End of plan.

## Progress update (delta)

Today I implemented a set of backend fixes to improve discovery accuracy and reduce false negatives. Changes made in this workspace:

- nas_discovery.py:
  - Added `mac_address` and `via_arp` fields to `NASDevice`.
  - Improved `_parse_ip_range` to reliably expand CIDR and range formats (supports single-octet ranges and full-range expansion).
  - Implemented `_scan_arp_table()` to read local ARP entries from `/proc/net/arp` or `arp -a` as a fallback.
  - Added `max_hosts` parameter to `discover_nas_devices` to cap scan size and avoid accidental wide scans.
  - Integrated ARP-fallback: when an IP has no open ports but appears in the ARP table, we now return it as an ARP-known device (with `via_arp: true`).

- nas_discovery_api_endpoints.py:
  - Accepts `max_hosts` in discovery requests and passes it to the discovery manager.
  - Includes `mac_address` and `via_arp` in API responses when present.

  Progress update (2025-08-17):

  - Implemented ARP-fallback preservation: ARP-derived entries are marked with `via_arp: true` and broadcast/multicast entries are filtered out by `routes/network_discovery.py`.
  - Added server-side and client-side scan caps (`max_hosts`) to prevent runaway CIDR scans. Server enforces bounds 1..1024 (default 254); client warns and caps at 254.
  - Normalized API responses in `routes/nas_core.py` to include `via_arp` for frontend compatibility.
  - Frontend `static/js/network-discovery.js` now computes CIDR host count, warns on large scans, and sends `max_hosts` to the server.
  - Added two unit tests (pytest): `test_ping_range_max_hosts_cap` and `test_enhanced_discovery_arp_fallback` under `backend/tests/` that mock network operations and validate cap and ARP behavior.

  Notes for next developer:
  - The tests use monkeypatch to avoid real network I/O; if running in CI, ensure pytest is available in the virtualenv.
  - Suggested next steps: add UI confirmation for scans >100 hosts and wire optional `nas_confidence_score` into `scan-device` port-scan responses.

  Progress update (UI confirmation):

  - Added a client-side confirmation prompt in `static/js/network-discovery.js` that triggers when an estimated scan size exceeds 100 hosts. The prompt uses `window.NASIntegration.core.confirm` if present (project-level modal), otherwise falls back to `window.confirm`.


Notes / next steps after these deltas:
- Wire these new response fields to the frontend table rendering (show "ARP" badge and persistent local name column).
- Add unit tests for `_parse_ip_range` and ARP-fallback behavior.
- Implement opt-in `scan_device` port scanning and `nas_confidence_score` next.

Status: Phase B work (CIDR + ARP fallback + host cap) partially completed — further tests and frontend wiring remain.
