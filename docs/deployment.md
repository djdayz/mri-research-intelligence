# Deployment

Production deployment is not yet implemented. The application now exposes the basic runtime hooks expected by a future deployment: `/health` for process liveness, `/ready` for database readiness, request correlation IDs, and JSON logs.

Required future work:

- Add a production Dockerfile running as a non-root user.
- Add `.dockerignore` and local compose configuration for API plus PostgreSQL.
- Configure SSL database URLs, secret storage outside source control, and migration execution.
- Add CI container build and optional deployment workflow.

Do not deploy with `.env` files or real credentials committed to source control.

Operational notes:

- Run `python -m alembic upgrade head` before serving traffic.
- Route load balancer readiness checks to `/ready`.
- Preserve or inject `x-request-id` at the edge; the API returns it on every response.
- Configure `MRINSIGHT_LLM_PROVIDER=fake` for offline demos and `MRINSIGHT_LLM_PROVIDER=openai` plus `MRINSIGHT_LLM_API_KEY` only for live LLM operation.
- Configure `MRINSIGHT_DIGEST_DELIVERY_PROVIDER=smtp` plus SMTP host/sender/auth variables for real email delivery. Keep SMTP credentials in the runtime secret store.
- Run `python -m mrinsight.cli digest run-due --rows 20` from cron, a container scheduler, or a cloud scheduled task; run `python -m mrinsight.cli digest retry-deliveries --limit 20` on a separate retry cadence.

Cron example:

```cron
*/30 * * * * cd /app && . /etc/mrinsight.env && python -m mrinsight.cli digest run-due --rows 20
*/15 * * * * cd /app && . /etc/mrinsight.env && python -m mrinsight.cli digest retry-deliveries --limit 20
```
