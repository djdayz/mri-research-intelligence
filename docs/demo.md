# Demo

Current local demo flow:

1. Start PostgreSQL.
2. Load environment variables.
3. Run `python -m alembic upgrade head`.
4. Start `python -m uvicorn mrinsight.main:app --reload`.
5. Ingest a DOI through the configured provider or test with the fake provider in automated tests.
6. Upload a generated or permitted PDF.
7. Compute relevance with `POST /papers/{paper_id}/relevance`.

Pending demo work:

- Seed command.
- Fake-provider CLI workflow.
- Fake structured analysis.
- Subscription and digest preview.
- Docker-based one-command demo.
