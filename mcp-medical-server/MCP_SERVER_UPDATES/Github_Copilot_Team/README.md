# Github Copilot Team — MCP Server Updates

**Folder Purpose:** Central repository for all Github Copilot team documentation and coordination related to Emergency Credential Retrieval System implementation.

**Last Updated:** 2025-11-07  
**Status:** Awaiting Kiro team agreement on coordination plan

---

## Folder Structure

```
Github_Copilot_Team/
├── README.md                          (this file)
├── TEAM_COORDINATION_PLAN.md          (5-phase implementation roadmap)
├── WORKER_PRODUCTIVITY_PLAN.md        (Architecture & design decisions)
├── SSO_SESSION_PLAN.md                (Session management & OAuth design)
└── PROJECT_TRACKING.md                (Todo list & progress tracker)
```

---

## Documents in This Folder

### 1. **TEAM_COORDINATION_PLAN.md**
**Purpose:** Detailed, non-blocking task breakdown for parallel execution across both teams.

**Contains:**
- 5-phase roadmap (weeks 1–10)
- 8 tasks for Github Copilot team (Phase 1)
- 20+ tasks for Kiro team (Phases 1–5)
- Weekly sync checkpoints
- Success criteria gates
- Dependency map (identifies all parallelizable work)

**Status:** Ready for Kiro team review

**Action:** Present to Kiro team lead for agreement before implementation starts.

---

### 2. **WORKER_PRODUCTIVITY_PLAN.md**
**Purpose:** High-level architecture, design decisions, and rationale for the system.

**Contains:**
- System architecture overview (offline-first, owner-controlled)
- Emergency credential retrieval workflow
- Approval flows (owner CLI + pre-auth + SLA escalation)
- Adapter architecture (SSH, SMB, WinRM, API, files)
- Onboarding & ephemeral account creation
- LLM integration strategy
- Owner-first guarantees & anti-vendor-lock measures
- NAS database access flows

**Status:** Final version (consensus with team)

**Use:** Reference for design questions & architecture discussions.

---

### 3. **SSO_SESSION_PLAN.md**
**Purpose:** Detailed OAuth2 + session tracking design for the MCP server.

**Contains:**
- SSO flow (Google + Microsoft)
- Session lifecycle management
- Token refresh strategy
- RBAC integration
- Multi-factor authentication hooks

**Status:** Completed design (not yet implemented)

**Use:** Reference for auth/session team.

---

### 4. **PROJECT_TRACKING.md**
**Purpose:** Live todo list tracking Phase 1–5 implementation progress.

**Contains:**
- Task breakdown by phase
- Completion status
- Blocker tracking
- Weekly milestone dates

**Status:** To be created and maintained throughout project

**Use:** Weekly sync checklist & progress reporting.

---

## How to Use This Folder

### For Kiro Team Lead Review
1. Read **TEAM_COORDINATION_PLAN.md** first (15 min read)
2. Review **WORKER_PRODUCTIVITY_PLAN.md** for architecture context (20 min read)
3. Schedule meeting with Github Copilot team lead to discuss:
   - Do tasks/phases align with Kiro team capacity?
   - Are there scheduling conflicts?
   - Which Kiro tasks should be adjusted/reordered?
   - Can Kiro team commit to weekly sync schedule?

### For Github Copilot Team Implementation
1. ✅ Read entire coordination plan
2. ✅ Create feature branch: `feature/emergency-credential-retrieval`
3. ✅ Start Phase 1 tasks (1.1, 1.2 in parallel)
4. ✅ Keep PROJECT_TRACKING.md updated daily
5. ✅ Schedule Friday EOD sync with Kiro team

### For Weekly Syncs
- Report progress using **TEAM_COORDINATION_PLAN.md** phase gates
- Update **PROJECT_TRACKING.md** before sync
- Review blockers + escalate immediately if any task is stuck >2x planned time

---

## Key Integration Points (Both Teams Must Agree)

### Token Format (Github Copilot Team → Kiro Team)
- Token claims structure (what fields must Kiro adapter check?)
- TTL defaults
- Nonce replay prevention mechanism
- Error response codes

### Vault Interface (Github Copilot Team ← → Kiro Team)
- Secret path naming convention
- Encryption at rest (Fernet key rotation?)
- Cache policies (TTL, owner approval flag)
- Error handling

### Merkle Audit Proofs (Both Teams)
- Proof format (JSON structure)
- Verification chain (how to prove no tampering)
- Event types (credential request, approval, retrieval, ephemeral account creation)
- Log replication from agents to central

### Approval Workflow (Github Copilot Team ← → Owner)
- CLI signature format
- Offline approval file format
- Pre-auth window syntax
- SLA escalation rules

---

## Communication Protocol

### Weekly Sync: Friday 3:00 PM
- **Duration:** 2 hours
- **Attendees:** Github Copilot lead + Kiro lead + key eng from each team
- **Agenda:**
  1. Github Copilot team status (15 min)
  2. Kiro team status (15 min)
  3. Integration check: do deliverables work together? (15 min)
  4. Blockers & escalations (10 min)
  5. Go/no-go decision for next phase (5 min)

### Escalation Path (If Blocked)
1. **Task Blocker:** Report in daily standup
2. **Team Blocker:** Escalate to team lead at EOD
3. **Cross-Team Blocker:** Notify both team leads + request emergency sync
4. **Critical Issue:** Page on-call architect

### Communication Tools
- GitHub Issues (tracking blockers)
- Weekly meeting notes (shared repo)
- Slack #mcp-emergency-creds channel (real-time questions)

---

## Success Metrics (Per Phase)

### Phase 1 (Weeks 1–2)
- Emergency request API working
- Owner CLI creates valid signatures
- Token replay prevention proven
- 80%+ test coverage
- **Demo:** End-to-end flow (request → approval → retrieval) runs without error

### Phase 2 (Weeks 3–4)
- All adapters (SSH, SMB, API, files) tested in isolation
- Agent installed + health check passes
- Token validation works with agent
- 80%+ test coverage

### Phase 3 (Weeks 5–6)
- Offline keygen produces valid keys
- Shamir shares reconstruct vault key
- Pre-auth + SLA escalation operational
- Full audit chain end-to-end

### Phase 4 (Weeks 7–8)
- Onboarding collects credentials successfully
- Ephemeral accounts created + auto-cleaned
- Dashboard displays metrics
- Ledger replication syncs

### Phase 5 (Weeks 9–10)
- Local LLM model provisioned
- Agent calls LLM for data enrichment
- Full documentation + runbooks complete
- Ready for production deployment

---

## Next Steps

### ✅ Github Copilot Team (Complete)
- [x] Created comprehensive coordination plan
- [x] Organized all docs in centralized folder
- [x] Ready to present to Kiro team

### 🔨 Github Copilot Team (Pending Kiro Agreement)
- [ ] Confirm Kiro team accepts task breakdown
- [ ] Schedule joint kick-off meeting
- [ ] Create shared communication channels
- [ ] Initialize Phase 1 feature branch
- [ ] Start Tasks 1.1 + 1.2

### 🔨 Kiro Team (Pending Agreement)
- [ ] Review coordination plan
- [ ] Identify scheduling conflicts
- [ ] Confirm team capacity (can you handle ~20+ tasks over 10 weeks?)
- [ ] Propose any adjustments to phase breakdown
- [ ] Commit to weekly sync schedule

---

## Escalation & Risk Mitigation

### Known Risks

| Risk | Mitigation |
|------|-----------|
| Kiro team unavailable during critical phase | Pre-plan coverage; async documentation |
| Integration test failures at gates | Weekly integration syncs; mock interfaces early |
| Security vulnerabilities in approval flow | Code review by security team before Phase 2 |
| Database schema changes block deployment | Backward-compatible migrations only |
| Owner approval CLI UX issues | Usability testing with practice owner before Phase 3 |

### Decision Log
- **2025-11-07:** Created coordination plan; awaiting Kiro team feedback
- (To be updated with team feedback)

---

## Contact & Ownership

- **Github Copilot Team Lead:** [Your name/contact]
- **Kiro Team Lead:** [Kiro lead contact]
- **Architecture Owner:** [Name]
- **Security Officer:** [Name]

---

## Related Folders

- **Parent:** `mcp-medical-server/MCP_SERVER_UPDATES/`
- **Kiro Team Folder:** `mcp-medical-server/MCP_SERVER_UPDATES/Kiro_Team/` (to be created by Kiro team with parallel docs)
- **Shared Code:** `mcp-medical-server/` (adapters, services, API endpoints)

---

**Document Status:** DRAFT - Awaiting Kiro team review & agreement  
**Last Review:** 2025-11-07  
**Next Review:** After Kiro team feedback (scheduled for [DATE TBD])

---

## Appendix: Quick Reference

### Phase 1 Your Team Tasks
1. Task 1.1: Extend audit service (2 days)
2. Task 1.2: Build request API (4 days)
3. Task 1.3: Owner approval CLI (3 days)
4. Task 1.4: Token issuer (4 days)
5. Task 1.5: Vault adapter (4 days)
6. Task 1.6: DB schema (2 days)
7. Task 1.7: E2E demo (3 days)
8. Task 1.8: Tests (4 days)

**Total Phase 1 Effort:** ~30 days (~6 weeks with parallelization)

### Phase 1 Kiro Team Tasks
- K1.1: Agent architecture design (3 days)
- K1.2: Adapter interface (2 days)
- K1.3: PKI design (2 days)

**Total Phase 1 Effort:** ~7 days (~1.5 weeks)

---

**All your team docs are now organized and ready for Kiro team discussion!**
