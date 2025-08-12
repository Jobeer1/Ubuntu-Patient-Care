# NAS Integration & Advanced DICOM Viewer: Progress & TODO

## Progress Summary

- **Backend foundation**: Flask backend, user DB, NAS connector, and REST endpoints are present.
- **2FA**: Core logic, endpoints, and admin/user flows implemented (see `README_2FA.md`).
- **DICOM Viewer**: React/TypeScript app scaffolded, with core viewing and measurement tools started.
- **Frontend**: Login, admin, user dashboards, and some NAS config UI exist.
- **Import tool**: `nas_importer.py` exists for NAS DICOM import/indexing.
- **Session management**: Single-session logic and endpoints present.
- **Secure link sharing**: Some backend and UI code for secure sharing.

## What Still Needs to Be Done


### Backend
- [ ] Complete user/group management (roles, permissions, LDAP/AD integration optional)
- [ ] Finalize secure link sharing (token generation, expiry, audit)
- [ ] NAS connector: error handling, reconnection, advanced config
- [ ] Per-user image access enforcement
- [ ] Audit logging for all admin/user actions
- [ ] Advanced authentication: face recognition, email 2FA
- [ ] Single-session enforcement: test all edge cases
- [ ] REST endpoints for all planned features (see plan)


### Frontend
- [ ] Complete admin/user dashboards (user/group management, permissions)
- [ ] NAS config/status dashboard, file browser UI
- [ ] DICOM viewer: finish advanced tools (3D, MPR, annotation, export)
- [ ] Secure link sharing UI (generate, copy, email, QR)
- [ ] Session expiration handling (notify user, redirect)
- [ ] Face/2FA UI (enrollment, verification)
- [ ] Localization (English, Afrikaans, isiZulu)

### Docs & Testing
- [ ] Update all READMEs with current status and usage
- [ ] Add user/admin guides (with South African context)
- [ ] Test with real NAS and DICOM datasets
- [ ] Document setup, security, and troubleshooting

---

*This TODO is based on the NAS_INTEGRATION_PLAN.md and current codebase. Please update as features are completed.*
