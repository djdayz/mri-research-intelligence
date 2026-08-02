# Release Checklist

- [ ] All quality gates pass.
- [ ] PostgreSQL migrations apply from base to head.
- [ ] Alembic reports one current head and no schema drift.
- [ ] API starts locally.
- [ ] Health, DOI ingestion, PDF upload, and relevance endpoints are exercised.
- [ ] No `.env`, private PDFs, local databases, or credentials are staged.
- [ ] Documentation reflects actual commands.
- [ ] Docker image builds after Docker support is added.
- [ ] Release tag is created only with explicit authorization.
