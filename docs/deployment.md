# Deployment

MRInsight is packaged as a containerized FastAPI service with PostgreSQL migrations run as an explicit release step.

## Local Compose

```bash
docker compose up --build api
```

The compose stack starts PostgreSQL, waits for database readiness, runs `python -m alembic upgrade head`, and then starts the API on `http://localhost:8000`. Digest files are written to a named volume.

Run one-shot background jobs locally:

```bash
docker compose --profile jobs run --rm digest-run-due
docker compose --profile jobs run --rm digest-retry-deliveries
```

## Container Image

The production image uses `python:3.11-slim`, installs only runtime dependencies, runs as the non-root `mrinsight` user, exposes port `8000`, and has a `/ready` health check.

Build manually:

```bash
docker build -t mrinsight-api:local .
```

Run migrations manually:

```bash
docker run --rm \
  -e MRINSIGHT_DATABASE_URL="$MRINSIGHT_DATABASE_URL" \
  mrinsight-api:local python -m alembic upgrade head
```

Run the API:

```bash
docker run --rm -p 8000:8000 \
  -e MRINSIGHT_DATABASE_URL="$MRINSIGHT_DATABASE_URL" \
  mrinsight-api:local
```

## Kubernetes Template

`deploy/kubernetes/mrinsight.yaml` provides:

- namespace;
- config map for non-secret environment values;
- secret template for database, LLM, Crossref, and SMTP values;
- migration job;
- API deployment and service;
- readiness and liveness probes;
- digest run and retry cron jobs.

Replace `ghcr.io/OWNER/mri-research-intelligence:TAG` with the image produced by CI. Create real secrets in the cluster or external secret manager; do not commit real secret values into the template.

## Required Environment

Sensitive values:

- `MRINSIGHT_DATABASE_URL`: use a managed PostgreSQL URL. Prefer SSL, for example `postgresql+psycopg://user:password@host:5432/dbname?sslmode=require`.
- `MRINSIGHT_CROSSREF_MAILTO`: real contact email for polite Crossref use.
- `MRINSIGHT_LLM_API_KEY`: only when `MRINSIGHT_LLM_PROVIDER=openai`.
- SMTP credentials when `MRINSIGHT_DIGEST_DELIVERY_PROVIDER=smtp`.

Operational database settings:

- `MRINSIGHT_DATABASE_POOL_SIZE`
- `MRINSIGHT_DATABASE_MAX_OVERFLOW`
- `MRINSIGHT_DATABASE_POOL_TIMEOUT_SECONDS`
- `MRINSIGHT_DATABASE_POOL_RECYCLE_SECONDS`

Use a least-privilege application database user that can read/write app tables and run migrations only from the migration job or release process. Keep backups and point-in-time restore enabled on managed PostgreSQL.

## Upload Limits

The app enforces `MRINSIGHT_PDF_MAX_BYTES`. Configure the same or lower request-body limit at the ingress, reverse proxy, or load balancer so oversized PDFs are rejected before reaching the application worker.

## CI/CD

`.github/workflows/deploy.yml` is manual-dispatch and environment-gated. It:

- runs migrations, Ruff, mypy, pytest, deterministic evaluation, and dependency audit;
- builds the Docker image;
- smoke-tests the installed package inside the image;
- scans the image with Trivy;
- optionally pushes to GitHub Container Registry;
- optionally runs environment-specific migration and release commands over SSH.

Configure GitHub environment secrets for staging and production:

- `DEPLOY_SSH_HOST`
- `DEPLOY_SSH_USER`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DEPLOY_MIGRATE_COMMAND`
- `DEPLOY_RELEASE_COMMAND`

Deployment is skipped unless `deploy=true` is selected. Publishing is skipped unless `publish_image=true` is selected. No cloud credentials or real secrets are committed.

## Rollback

Keep at least one previous image tag available in the registry. To roll back, redeploy the previous image tag and verify `/ready`. Schema downgrades should be treated as exceptional; prefer backward-compatible migrations and roll forward when possible. If a migration must be reversed, run the tested Alembic downgrade manually after taking a database backup.
