# MCP_SERVER_UPDATES — Documentation & Coordination Hub

**Last Updated:** 2025-11-07  
**Purpose:** Central repository for all team documentation related to emergency credential retrieval system and MCP server enhancements.

---

## Folder Structure

```
MCP_SERVER_UPDATES/
├── README.md (this file)
├── Github_Copilot_Team/
│   ├── README.md                      (team overview + folder guide)
│   ├── TEAM_COORDINATION_PLAN.md      (5-phase parallel implementation roadmap)
│   ├── WORKER_PRODUCTIVITY_PLAN.md    (architecture + design decisions)
│   ├── SSO_SESSION_PLAN.md            (OAuth + session management)
│   └── PROJECT_TRACKING.md            (progress board + milestones)
│
├── Kiro_Team/ (to be created by Kiro team with parallel docs)
│   ├── README.md
│   ├── TASK_BREAKDOWN.md
│   └── ... (other Kiro docs)
│
└── Shared/
    ├── INTEGRATION_POINTS.md          (token format, vault interface, etc.)
    └── WEEKLY_SYNC_NOTES.md           (meeting minutes)
```

---

## Document Index

### Github_Copilot_Team Folder

All documents related to the Github Copilot team's work on emergency credential retrieval.

| Document | Purpose | Status | Last Updated |
|----------|---------|--------|--------------|
| **README.md** | Team overview, folder guide, communication protocol | Ready | 2025-11-07 |
| **TEAM_COORDINATION_PLAN.md** | 5-phase detailed task breakdown (non-blocking parallel work) | Ready | 2025-11-07 |
| **WORKER_PRODUCTIVITY_PLAN.md** | System architecture, design decisions, constraints | Ready | 2025-11-07 |
| **SSO_SESSION_PLAN.md** | OAuth2 + session tracking design (not yet implemented) | Ready | 2025-11-07 |
| **PROJECT_TRACKING.md** | Live todo list, progress board, milestones | Ready | 2025-11-07 |

### Kiro_Team Folder (Pending Creation)

The Kiro team will create and maintain parallel documentation showing:
- Their task breakdown for Phases 1–5
- Adapter implementation details
- Agent architecture
- Integration points with Github Copilot team

**Status:** Awaiting Kiro team setup

---

## How to Use This Hub

### For Project Leads
1. Review **Github_Copilot_Team/TEAM_COORDINATION_PLAN.md** (20 min)
2. Have Kiro team lead review same document
3. Schedule kickoff meeting with both teams
4. Confirm integration points (token format, vault interface)
5. Initialize both team folders + communication channels

### For Developers
1. Navigate to your team's folder
2. Read the team README for context
3. Reference the TEAM_COORDINATION_PLAN.md for your assigned tasks
4. Track progress in PROJECT_TRACKING.md
5. Report blockers in weekly syncs

### For Weekly Syncs
1. Both teams report status against TEAM_COORDINATION_PLAN.md
2. Review integration points from Shared/INTEGRATION_POINTS.md
3. Identify blockers and escalate immediately
4. Update Shared/WEEKLY_SYNC_NOTES.md
5. Make go/no-go decision for next phase

---

## Key Coordination Dates

| Event | Date | Time | Attendees |
|-------|------|------|-----------|
| Kiro Team Reviews Plan | TBD | TBD | Kiro Lead |
| Kickoff Meeting | TBD | TBD | Both Team Leads + Eng Leads |
| Phase 1 Sync (Gate) | 2025-11-22 | 3:00 PM | Both Teams |
| Phase 2 Sync (Gate) | 2025-12-06 | 3:00 PM | Both Teams |
| Phase 3 Sync (Gate) | 2025-12-20 | 3:00 PM | Both Teams |
| Phase 4 Sync (Gate) | 2026-01-03 | 3:00 PM | Both Teams |
| Phase 5 Sync (Gate) | 2026-01-17 | 3:00 PM | Both Teams |

---

## Critical Coordination Points

### 1. **Token Format** (Github Copilot → Kiro)
- Must be finalized before Phase 2 starts
- Document in `Shared/INTEGRATION_POINTS.md`
- Example: `{"iss": "mcp-server", "aud": "mcp-agent", "req_id": "...", "vault": "...", "path": "...", "exp": ..., "nonce": "...", "sig": "..."}`

### 2. **Vault Interface** (Both Teams)
- Secret path naming convention
- Encryption at rest (Fernet vs Vault)
- Cache policies (TTL, owner approval flag)
- Error codes and handling

### 3. **Merkle Audit Proofs** (Both Teams)
- Event types: `CREDENTIAL_REQUEST`, `CREDENTIAL_APPROVED`, `CREDENTIAL_RETRIEVED`, `CREDENTIAL_EPHEMERAL_CREATED`
- Proof format for chain verification
- Ledger replication protocol

### 4. **Approval Workflow** (Github Copilot + Owner)
- CLI signature format
- Pre-auth window syntax
- SLA escalation rules
- Debrief completion tracking

---

## Communication Protocol

### Async Communication
- **Slack Channel:** #mcp-emergency-creds
- **GitHub Issues:** Track blockers and decisions
- **Email:** For formal decisions and escalations

### Synchronous (Weekly Syncs)
- **Day:** Friday
- **Time:** 3:00 PM
- **Duration:** 2 hours
- **Attendees:** Team leads + tech leads + key engineers

### Escalation Path
1. **Task Blocker:** Report in standup
2. **Team Blocker:** Escalate to team lead at EOD
3. **Critical Issue:** Emergency sync + page architect

---

## Success Metrics

### Phase 1 (Weeks 1–2)
- ✅ Emergency request API working
- ✅ Owner CLI creates valid signatures
- ✅ Token replay prevention proven
- ✅ End-to-end demo runs without error

### Phase 2 (Weeks 3–4)
- ✅ All adapters tested independently
- ✅ Agent deployed + health check passes
- ✅ Integration tests passing

### Phases 3–5
- ✅ Full system operational
- ✅ Offline operation verified
- ✅ Owner control guaranteed
- ✅ Documentation complete

---

## How to Request Changes

If either team needs to modify the coordination plan:
1. Open a GitHub issue with proposed change
2. Tag both team leads for review
3. Schedule a 15-min sync if needed
4. Document decision in Shared/WEEKLY_SYNC_NOTES.md
5. Update relevant plan documents

---

## Next Immediate Steps

### For Github Copilot Team Lead
- [ ] Review TEAM_COORDINATION_PLAN.md
- [ ] Prepare for presentation to Kiro team
- [ ] Schedule kickoff meeting with Kiro lead
- [ ] Prepare Phase 1 onboarding for dev team

### For Kiro Team Lead
- [ ] Read TEAM_COORDINATION_PLAN.md (20 min)
- [ ] Review WORKER_PRODUCTIVITY_PLAN.md for architecture (20 min)
- [ ] Identify any capacity or scheduling concerns
- [ ] Respond with feedback/agreement to proceed

### For Both Teams
- [ ] Create shared communication channels
- [ ] Establish escalation contacts
- [ ] Schedule first Friday sync for 2025-11-22
- [ ] Prepare demo environment for Phase 1

---

## Related Documentation

**Outside this folder but referenced:**
- `mcp-medical-server/SSO_SESSION_PLAN.md` (existing, same as in Github_Copilot_Team folder)
- `mcp-medical-server/WORKER_PRODUCTIVITY_PLAN.md` (existing, same as in Github_Copilot_Team folder)
- `audit/report_finalizer.py` (Merkle audit ledger — existing)
- `Team-Copilot/README.md` (CredMgr + Fernet — existing)
- `4-PACS-Module/NASIntegration/` (existing code for reuse)

---

## Escalation Contacts

- **Github Copilot Lead:** [Name/Contact TBD]
- **Kiro Lead:** [Name/Contact TBD]
- **Architecture Owner:** [Name/Contact TBD]
- **Security Officer:** [Name/Contact TBD]

---

## Document Status

| Document | Created | Status | Review | Approval |
|----------|---------|--------|--------|----------|
| TEAM_COORDINATION_PLAN.md | 2025-11-07 | Ready | Github Copilot | Pending Kiro |
| WORKER_PRODUCTIVITY_PLAN.md | 2025-11-07 | Ready | Github Copilot | Approved |
| PROJECT_TRACKING.md | 2025-11-07 | Ready | Github Copilot | Approved |
| SSO_SESSION_PLAN.md | 2025-11-07 | Ready | Github Copilot | Approved |

---

**Last Review:** 2025-11-07  
**Next Review:** After Kiro team feedback (TBD)

**This folder is your central coordination hub. Keep documents up-to-date and refer to them in every team meeting.**
