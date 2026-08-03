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
- [ ] No `.env`, private PDFs, local databases, or credentials are staged.
- [ ] Documentation reflects actual commands.
- [ ] Docker image builds after Docker support is added.
- [ ] Release tag is created only with explicit authorization.
