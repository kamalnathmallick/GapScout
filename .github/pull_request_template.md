## Description
<!-- Provide a concise summary of the changes and the problem solved. -->

## Type of Change
- [ ] New feature (`feat`)
- [ ] Bug fix (`fix`)
- [ ] Refactoring / optimization (`refactor`)
- [ ] Documentation update (`docs`)
- [ ] Infrastructure / CI (`chore`)

## Quality & Verification Checklist
- [ ] Code passes formatting and lint checks (`make lint`).
- [ ] Backend tests pass (`make test`).
- [ ] Frontend unit tests pass (`npm --prefix apps/web test`).
- [ ] If new database state is required, a new versioned Alembic migration was added.
- [ ] No secrets, credentials, or `.env` files are committed.
- [ ] Any external fetching adheres to SSRF safety rules.
