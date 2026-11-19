# GapScout build progress

Settings are in BUILD_PLAN.md (RUN_MODE, BUILD_PATH, DEPLOY_TARGET).

## Checklist
- [x] Bootstrap (project files created, tools verified)
- [ ] Prompt 1: Repo scaffold and dev environment
- [ ] Prompt 2: Database schema and migrations
- [ ] Prompt 3: Data source layer and scraper integration
- [ ] Prompt 4: Grid planner and job orchestration
- [ ] Prompt 5: Cleaning, normalisation and deduplication
- [ ] Prompt 6: Gap analysis engine
- [ ] Prompt 7: Backend API
- [ ] Prompt 8: Frontend foundation
- [ ] Prompt 9: Gap map UI
- [ ] Prompt 10: Lead features and rule-based scorer
- [ ] Prompt 11: LLM enrichment
- [ ] Prompt 12: Outreach workflow
- [ ] Prompt 13: Outcome logging and dataset builder
- [ ] Prompt 14: ML training pipeline
- [ ] Prompt 15: Model insights and active learning
- [ ] Prompt 16: Auth, tenancy and settings
- [ ] Prompt 17: Compliance and security hardening
- [ ] Prompt 18: Testing and quality
- [ ] Prompt 19: Observability and operations
- [ ] Prompt 20: Deployment and CI/CD
- [ ] Prompt 21: Demo data, docs and portfolio packaging

## Log
(newest first. For each finished prompt: date, what changed, how to run, how to test, decisions and deviations)

### 2026-11-19 - Bootstrap
- Verified tools: git 2.56.0, Docker 29.9.3 + Compose v5.7.0 (linux containers), Node v24.21.0, Python 3.12.10 + pip 25.0.1, GNU Make 4.4.1.
- Created AGENTS.md (Section 6 verbatim), CLAUDE.md, GEMINI.md, PROGRESS.md (Section 7 verbatim).
- Settings: RUN_MODE=checkpoints, BUILD_PATH=portfolio, DEPLOY_TARGET=A.
- Deviation: host is Windows 11, not Linux. Commands are run through PowerShell; GNU Make installed via winget (ezwinports.make) and lives on the user PATH. Compose services stay Linux containers.
- Blockers: none.

## Blockers
(anything that needs the human: credentials, installs, decisions)
