from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_uses_non_root_runtime_with_healthcheck() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim AS runtime" in dockerfile
    assert "pip install ." in dockerfile
    assert "USER mrinsight" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/ready" in dockerfile
    assert "--proxy-headers" in dockerfile


def test_dockerignore_excludes_local_secrets_and_caches() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert ".venv" in dockerignore
    assert ".git" in dockerignore
    assert "tests" in dockerignore
    assert "var" in dockerignore


def test_compose_defines_database_migration_api_and_job_services() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "db:" in compose
    assert "migrate:" in compose
    assert "api:" in compose
    assert "digest-run-due:" in compose
    assert "digest-retry-deliveries:" in compose
    assert "service_completed_successfully" in compose
    assert "/ready" in compose


def test_deploy_workflow_builds_scans_publishes_and_runs_migrations() -> None:
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")

    assert "python -m pytest" in workflow
    assert "python -m pip_audit" in workflow
    assert "setuptools>=83.0.0" in workflow
    assert "docker build" in workflow
    assert "aquasecurity/trivy-action@v0.33.1" in workflow
    assert "continue-on-error: ${{ !inputs.publish_image }}" in workflow
    assert "docker push" in workflow
    assert "DEPLOY_MIGRATE_COMMAND" in workflow
    assert "DEPLOY_RELEASE_COMMAND" in workflow


def test_kubernetes_manifest_has_readiness_migration_and_cronjobs() -> None:
    manifest = (ROOT / "deploy/kubernetes/mrinsight.yaml").read_text(encoding="utf-8")

    assert "kind: Job" in manifest
    assert 'python", "-m", "alembic", "upgrade", "head' in manifest
    assert "readinessProbe:" in manifest
    assert "path: /ready" in manifest
    assert "kind: CronJob" in manifest
    assert "digest-run-due" in manifest
    assert "retry-deliveries" in manifest
