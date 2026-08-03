# Release Checklist

- [ ] All quality gates pass.
- [ ] PostgreSQL migrations apply from base to head.
- [ ] Alembic reports one current head and no schema drift.
- [ ] API starts locally.
- [ ] `/health` and `/ready` return successful responses.
- [ ] DOI ingestion, relevance, analysis, retrieval, subscription, digest preview, and digest retrieval endpoints are exercised.
- [ ] Duplicate insert recovery tests pass for papers, content, chunks, relevance, analysis, digests, and deliveries.
- [ ] Request logs include `request_id`, method, path, status code, and duration without request bodies.
- [ ] Demo subscription seed command is repeatable.
- [ ] Deterministic golden evaluation report has zero failed cases.
- [ ] Docker image builds and starts with `/ready` passing.
- [ ] Compose migration and API services start successfully.
- [ ] Deployment workflow image build and scan pass.
- [ ] No `.env`, private PDFs, local databases, or credentials are staged.
- [ ] Documentation reflects actual commands.
- [ ] Production secrets are stored outside source control.
- [ ] Release tag is created only with explicit authorization.
