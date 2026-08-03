# Release Checklist

- [x] All local quality gates pass.
- [x] PostgreSQL migrations apply from base to head in a clean reset test database schema.
- [x] Alembic reports one current head and no schema drift.
- [x] API starts locally.
- [x] `/health` and `/ready` return successful responses.
- [x] DOI ingestion, relevance, analysis, retrieval, subscription, digest preview, and digest retrieval endpoints are exercised through the fake-provider API workflow.
- [x] Duplicate insert recovery tests pass for papers, content, chunks, relevance, analysis, digests, and deliveries.
- [x] Request logs include `request_id`, method, path, status code, and duration without request bodies.
- [x] Demo subscription seed command is repeatable.
- [x] Deterministic golden evaluation report has zero failed cases.
- [ ] Docker image builds and starts with `/ready` passing. Not locally verified because Docker is not installed in this environment.
- [ ] Compose migration and API services start successfully. Not locally verified because Docker is not installed in this environment.
- [ ] Deployment workflow image build and scan pass in GitHub Actions after PR.
- [x] No `.env`, private PDFs, local databases, or credentials are staged. The only tracked PDF is the generated synthetic demo PDF.
- [x] Documentation reflects actual commands.
- [x] Production secrets are stored outside source control.
- [ ] Release tag is created only with explicit authorization.
