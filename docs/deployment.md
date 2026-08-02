# Deployment

Production deployment is not yet implemented.

Required future work:

- Add a production Dockerfile running as a non-root user.
- Add `.dockerignore` and local compose configuration for API plus PostgreSQL.
- Configure SSL database URLs, secret storage outside source control, and migration execution.
- Add readiness checks separate from liveness.
- Add CI container build and optional deployment workflow.

Do not deploy with `.env` files or real credentials committed to source control.
