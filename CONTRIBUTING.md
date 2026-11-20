# Contributing to GapScout

Thank you for your interest in contributing to GapScout! We welcome issues, bug reports, and pull requests.

---

## Development Setup

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Linux container engine running.
- [GNU Make](https://www.gnu.org/software/make/) (`winget install --id ezwinports.make -e` on Windows).
- Python 3.11+ and Node.js 20+ (if running tooling outside Docker).

### 2. Local Environment
```bash
git clone https://github.com/kamalnathmallick/GapScout.git
cd GapScout

# Spin up local containers (PostGIS, Redis, FastAPI, Celery, Scraper, Next.js)
make up

# Run migrations
make migrate
```

---

## Code Quality & Testing

All contributions must pass automated tests and linters before being merged.

### Backend (Python / FastAPI)
```bash
# Run pytest test suite in the API container
make test

# Format and lint with Ruff
make lint
```

### Frontend (Next.js / TypeScript)
```bash
# Run Vitest unit tests
npm --prefix apps/web test

# Run TypeScript type check and ESLint
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
```

### End-to-End Tests (Playwright)
```bash
npx --prefix tests-e2e playwright test
```

---

## Engineering Guidelines

1. **Strict Type Safety:** Type hints are required for all Python code; strict typing is enforced for TypeScript (`noImplicitAny`).
2. **Database Migrations:** Never edit past Alembic migrations. Always create a new versioned migration with `alembic revision --autogenerate -m "description"`.
3. **SSRF & Safety First:**
   - Any external web fetcher must strictly validate URLs and reject private, loopback, or non-routable IP addresses.
   - Scraped text from websites or reviews is treated as untrusted passive data, never instructions to an LLM.
4. **No Direct Outreach:** The application prepares drafts and analysis; it never sends emails or messages automatically.
5. **No Secrets in Git:** Never commit `.env` or credentials. Keep `.env.example` up to date.

---

## Pull Request Process

1. Fork the repository and create your feature branch: `git checkout -b feat/your-feature-name`.
2. Commit your changes with clear, semantic commit messages (e.g. `feat(...)`, `fix(...)`, `docs(...)`).
3. Ensure all tests (`make test`, `npm test`) pass locally.
4. Push to your branch and open a Pull Request against `main`.
