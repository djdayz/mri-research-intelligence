# Demo

## Local API Demo

```bash
set -a
source .env
set +a
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m mrinsight.cli seed demo
MRINSIGHT_LLM_PROVIDER=fake .venv/bin/python -m uvicorn mrinsight.main:app --reload
```

In another shell:

```bash
BASE_URL=http://localhost:8000 DEMO_DOI=<crossref-resolvable-doi> ./scripts/demo_workflow.sh
```

The script checks `/health` and `/ready`, ingests a DOI through the configured bibliographic provider, computes relevance, generates an analysis with the configured LLM provider, and reads the retrieval views. Use `MRINSIGHT_LLM_PROVIDER=fake` for an offline analysis demo after metadata has been resolved. A live OpenAI run requires `MRINSIGHT_LLM_PROVIDER=openai` and `MRINSIGHT_LLM_API_KEY`.

## Digest Demo

`python -m mrinsight.cli seed demo` creates a repeatable subscription named `Demo MRI CVR weekly digest`. Run a digest preview with:

```bash
.venv/bin/python -m mrinsight.cli digest run --subscription-id 1 --rows 10
```

When Crossref mailto settings are absent, discovery uses the deterministic empty fake provider. With `MRINSIGHT_CROSSREF_MAILTO` configured, the digest preview uses Crossref metadata search and writes previews through the file delivery provider under `var/digests`.

See `docs/demo-fixture.json` for the canonical demo payloads.

## SMTP Delivery Demo

Set:

```bash
MRINSIGHT_DIGEST_DELIVERY_PROVIDER=smtp
MRINSIGHT_SMTP_HOST=smtp.example.org
MRINSIGHT_SMTP_PORT=587
MRINSIGHT_SMTP_SENDER=sender@example.org
MRINSIGHT_SMTP_USERNAME=<optional-username>
MRINSIGHT_SMTP_PASSWORD=<optional-password>
```

Create or update a subscription with `delivery_destination` set to the recipient email address. The SMTP provider sends both plain-text and HTML bodies. It validates a single recipient address, uses the configured timeout, performs bounded retries, and records the message ID as the provider response ID.

## Scheduled Demo Commands

These commands run once and exit, which makes them suitable for cron or a container scheduler:

```bash
.venv/bin/python -m mrinsight.cli digest run-due --rows 20
.venv/bin/python -m mrinsight.cli digest retry-deliveries --limit 20
```
