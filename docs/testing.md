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
