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

SMTP delivery tests inject a fake SMTP client and never contact a live server. Live email delivery is a manual smoke test only after SMTP credentials and a test recipient are configured.

Run deterministic golden LLM evaluation:

```bash
.venv/bin/python -m mrinsight.cli eval run --output var/evaluation/golden-report.json
```

This uses synthetic cases and the fake LLM provider by default. Live-model evaluation requires `--provider configured --allow-live` and should not be a required CI gate.

Deployment artifact checks are covered by `tests/unit/test_deployment_artifacts.py`. A real Docker image build requires Docker to be installed:

```bash
docker build -t mrinsight-api:local .
docker compose up --build api
```
