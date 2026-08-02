# Architecture

MRInsight is a modular monolith:

```mermaid
flowchart TD
    API["FastAPI routers"] --> Services["Application services"]
    Services --> Domain["Domain records and protocols"]
    Services --> NLP["Deterministic NLP and relevance"]
    Services --> Repositories["Repository protocols"]
    Repositories --> Adapters["SQLAlchemy adapters"]
    Adapters --> Postgres["PostgreSQL"]
    Services --> Providers["External provider adapters"]
```

FastAPI routes own request/response mapping. Application services own workflow decisions. Repositories flush but do not commit; request-scoped dependencies own commit and rollback.

The deterministic evidence path is:

```mermaid
flowchart LR
    DOI["DOI"] --> Paper["Paper metadata"]
    Paper --> Content["Abstract or PDF text"]
    Content --> Chunks["Section-aware chunks"]
    Chunks --> Relevance["Rule relevance assessment"]
```
