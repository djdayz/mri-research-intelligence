# Testing

Run the main gates:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
.venv/bin/python -m pytest
```

Run migration checks:

```bash
set -a
source .env
set +a
.venv/bin/python -m alembic current --check-heads
.venv/bin/python -m alembic check
```

Database tests require PostgreSQL. Normal tests use fake providers and generated PDFs; they must not call live Crossref, LLM, email, or discovery services.

Focused MVP hardening checks:

```bash
.venv/bin/python -m pytest \
  tests/integration/db/test_conflict_recovery.py \
  tests/api/test_mvp_workflow.py \
  tests/api/test_health.py
```

`tests/api/test_mvp_workflow.py` is the public API end-to-end path for the MVP. It uses fake metadata, fake LLM, fake discovery, and fake delivery providers.
