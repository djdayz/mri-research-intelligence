# Architecture

MRInsight is a modular monolith. FastAPI maps HTTP requests, application services coordinate workflows, domain records define boundaries, repositories persist state, and provider adapters isolate external services.

## Component Architecture

```mermaid
flowchart TD
    Client["API clients and CLI"] --> API["FastAPI routers"]
    API --> Services["Application services"]
    Services --> Papers["Paper domain records"]
    Services --> NLP["Text cleaning, sections, chunking"]
    Services --> Relevance["Deterministic relevance"]
    Services --> Analysis["LLM analysis service"]
    Services --> Discovery["Discovery and digest services"]
    Services --> Repositories["Repository protocols"]
    Repositories --> SQLAlchemy["SQLAlchemy adapters"]
    SQLAlchemy --> Postgres["PostgreSQL"]
    Analysis --> LLMProviders["Fake or OpenAI provider"]
    Discovery --> DiscoveryProviders["Fake or Crossref provider"]
    Discovery --> DeliveryProviders["File, console, fake, or SMTP delivery"]
```

FastAPI routes own request and response mapping. Services own workflow decisions. Repositories flush but do not commit; request-scoped dependencies own commit and rollback.

## DOI Ingestion

```mermaid
sequenceDiagram
    participant Client
    participant API as "POST /papers"
    participant Service as "IngestPaperService"
    participant Provider as "Bibliographic provider"
    participant Repo as "Paper repository"
    participant DB as "PostgreSQL"

    Client->>API: DOI payload
    API->>Service: normalized request
    Service->>Provider: fetch metadata
    Provider-->>Service: title, abstract, journal, dates, provenance
    Service->>Repo: add or recover duplicate paper
    Repo->>DB: insert with DOI/title constraints
    Service->>Repo: store abstract content and chunks when available
    API-->>Client: persisted paper response
```

## PDF Extraction

```mermaid
flowchart LR
    Upload["Permitted PDF upload"] --> Validate["MIME, extension, size, and parser validation"]
    Validate --> Extract["pypdf extraction"]
    Extract --> Pages["page-level text records"]
    Pages --> Clean["text cleaning and checksum"]
    Clean --> Sections["section detection"]
    Sections --> Chunks["section-aware evidence chunks"]
    Chunks --> Content["full-text content state"]
    Content --> DB["PostgreSQL"]
```

PDF extraction records parser version, checksum, extraction status, page offsets, chunk ranges, and failure reasons. The app does not OCR scanned documents.

## Analysis

```mermaid
flowchart TD
    Paper["Paper"] --> Select["Select best content"]
    Select --> Evidence["Select evidence chunks"]
    Evidence --> Prompt["Assemble versioned prompt"]
    Prompt --> Provider["Fake or OpenAI LLM provider"]
    Provider --> Parse["Parse strict JSON schema"]
    Parse --> Validate["Evidence, scope, and numerical validation"]
    Validate -->|valid| Store["Persist LLM run and analysis"]
    Validate -->|invalid| Repair["One repair request"]
    Repair --> Parse
    Validate -->|still invalid| Failure["Persist honest failure diagnostics"]
    Store --> API["Analysis API response"]
```

The LLM cannot introduce uncited reported claims. Abstract-only evidence cannot be labelled as full text. Numerical results must cite evidence containing the value text.

## Discovery And Digest

```mermaid
flowchart TD
    Topic["Topic rules and query"] --> Subscription["Subscription"]
    Subscription --> Search["Fake or Crossref discovery search"]
    Search --> Candidates["Discovery candidates"]
    Candidates --> Dedupe["DOI and title/year deduplication"]
    Dedupe --> Ingest["Candidate ingestion"]
    Ingest --> Relevance["Relevance assessment"]
    Relevance --> Rank["Thresholding and ranking"]
    Rank --> Digest["Plain-text and HTML digest"]
    Digest --> Delivery["File, console, fake, or SMTP delivery"]
    Delivery --> Retry["Retry metadata for failed deliveries"]
```

Manual previews and scheduled one-shot CLI commands use the same service path.

## Data Model

```mermaid
erDiagram
    PAPERS ||--o{ PAPER_CONTENTS : has
    PAPER_CONTENTS ||--o{ PAPER_CONTENT_PAGES : contains
    PAPER_CONTENTS ||--o{ PAPER_CHUNKS : chunks
    PAPERS ||--o{ PAPER_RELEVANCE_ASSESSMENTS : scored
    PAPERS ||--o{ PAPER_ANALYSES : analyzed
    PAPER_CONTENTS ||--o{ PAPER_ANALYSES : supports
    LLM_RUNS ||--o| PAPER_ANALYSES : produces
    TOPICS ||--o{ SUBSCRIPTION_TOPICS : selected
    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_TOPICS : includes
    SUBSCRIPTIONS ||--o{ DISCOVERY_RUNS : runs
    DISCOVERY_RUNS ||--o{ DISCOVERY_CANDIDATES : returns
    SUBSCRIPTIONS ||--o{ DIGESTS : generates
    DIGESTS ||--o{ DIGEST_DELIVERIES : delivers
```

JSONB is used for structured diagnostics and versioned payloads at repository boundaries: relevance categories, matched concepts, selected chunk IDs, validation errors, topic rules, preferred categories, analyses, and digest selected-paper payloads.

## Deployment

```mermaid
flowchart TD
    GitHub["GitHub Actions manual workflow"] --> Quality["Ruff, mypy, pytest, Alembic, eval, pip-audit"]
    Quality --> Build["Docker build"]
    Build --> Scan["Trivy image scan"]
    Scan --> Registry["Optional GHCR push"]
    Registry --> Migrate["Environment migration command"]
    Migrate --> Release["Environment release command"]
    Release --> API["Containerized FastAPI service"]
    API --> ManagedDB["Managed PostgreSQL with SSL"]
    Scheduler["CronJob or scheduler"] --> DigestCLI["Digest CLI commands"]
    DigestCLI --> ManagedDB
    API --> Probes["/health and /ready probes"]
```

Deployment is intentionally gated. Image publishing and deployment run only when selected, and real secrets stay in the target environment or secret store.
