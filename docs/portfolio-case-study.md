# Portfolio Case Study

MRInsight is a production-quality research software portfolio project for MRI literature intelligence. It demonstrates backend engineering, deterministic NLP, LLM safety boundaries, PostgreSQL modelling, CI, deployment preparation, and honest scientific communication.

## Problem

MRI researchers need to triage a fast-moving literature stream without losing provenance. A useful assistant must keep metadata, abstract evidence, uploaded full text, relevance scoring, and generated analysis separate enough that a reader can tell what was observed, what was inferred, and what is unavailable.

The project focuses on a narrow, defensible workflow:

- ingest papers by DOI;
- retain provider provenance;
- accept only permitted PDF uploads;
- extract and chunk evidence deterministically;
- score MRI, CVR, machine-learning, and deep-learning relevance;
- generate structured analysis only from supplied chunks;
- create digests for recurring topic monitoring.

## Users

Primary users are MRI researchers, medical-imaging R&D teams, research software engineers, and applied AI teams evaluating paper triage workflows. The system is not a clinical decision tool and does not claim complete literature coverage.

## Architecture

MRInsight is a modular monolith with explicit boundaries:

- FastAPI routers handle HTTP mapping.
- Application services own workflow decisions.
- Domain records and protocols define contracts.
- SQLAlchemy repositories persist state through PostgreSQL.
- Provider adapters isolate Crossref, OpenAI, SMTP, and deterministic fakes.
- NLP components clean text, detect sections, chunk evidence, and score relevance before any LLM call.

Detailed Mermaid diagrams are in [architecture.md](architecture.md).

## Engineering Challenges

The hardest part was keeping the system useful without collapsing scientific boundaries. Abstract-only evidence can support a limited analysis, but it must never be presented as full text. Uploaded PDFs can improve evidence coverage, but extraction quality and upload legality remain explicit constraints. LLM responses can summarize supplied evidence, but every reported or uncertain claim must cite persisted chunks.

The persistence layer also had to behave like a real service. The repositories use PostgreSQL-specific integration tests, uniqueness constraints, Alembic migrations, and duplicate insert recovery rather than relying on SQLite shortcuts.

## Scientific-Safety Choices

MRInsight treats evidence as a first-class object:

- every content record has type, extraction status, parser version, checksum, and timestamps;
- page records preserve PDF page text boundaries;
- chunks preserve section, character ranges, page ranges, and chunker version;
- relevance assessments include category scores, matched concepts, diagnostics, and model versions;
- LLM analyses persist provider, model, prompt, schema, selected chunk IDs, token usage, request IDs, latency, status, validation errors, and cache identity.

The analysis schema distinguishes `reported`, `uncertain`, `not_reported`, `unavailable_abstract_only`, and `unsupported` information. Reported and uncertain claims require evidence references. Numerical results must cite evidence containing the value text.

## Deterministic Versus LLM Responsibilities

Deterministic code is responsible for DOI normalization, title normalization, text cleaning, section detection, chunking, content selection, evidence selection, relevance scoring, pagination, filtering, idempotency, and validation.

The LLM is responsible only for producing a structured analysis from supplied evidence chunks. The provider response is parsed, validated, optionally repaired once, and rejected if it still violates schema, evidence, numerical, or scope rules. Normal tests use deterministic fakes and never require live provider calls.

## Testing Strategy

The test suite covers API routes, application services, repository behavior, PostgreSQL migrations, deterministic NLP, relevance scoring, LLM schema validation, fake-provider repair paths, retrieval filters, discovery/digest workflows, SMTP behavior through fakes, deployment artifacts, and portfolio demo assets.

Quality gates are:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest
python -m alembic current --check-heads
python -m alembic check
python -m mrinsight.cli eval run --output var/evaluation/golden-report.json
```

## Deployment

The repository includes a non-root production Dockerfile, local Docker Compose stack for API plus PostgreSQL, Kubernetes manifests, configurable database pooling, readiness and liveness probes, explicit migration jobs, digest cron jobs, and a manual GitHub Actions deployment workflow.

No real cloud credentials, production domains, private PDFs, API keys, or SMTP credentials are committed. Live deployment remains an external operational step because it depends on the target account and secret store.

## Demonstration Assets

Synthetic, legally reusable demo assets are in [demo-assets](demo-assets):

- `synthetic-mri-cvr-paper.pdf`;
- `sample-api-requests.http`;
- `sample-fake-provider-response.json`;
- `sample-analysis-output.json`;
- `sample-fake-evaluation-report.json`;
- `sample-digest.txt`;
- `sample-digest.html`;
- `sample-cli-transcript.txt`.

Regenerate them with:

```bash
.venv/bin/python scripts/generate_demo_assets.py
```

## Trade-Offs

- pypdf is simple and deployable, but it is not a layout-understanding or OCR engine.
- The deterministic relevance baseline is explainable and testable, but it is not a clinically validated classifier.
- The LLM layer is intentionally constrained; this reduces flexibility but protects provenance and unsupported-claim handling.
- The app is a modular monolith rather than microservices because the current workflow benefits from transactional boundaries and low operational overhead.
- Deployment manifests are provider-neutral templates; production hardening still requires environment-specific secrets, DNS, observability retention, and managed database policy choices.

## Future Improvements

- OCR and layout-aware PDF extraction for scanned or complex articles.
- Human review queues for questionable extractions and low-confidence analyses.
- Learned relevance ranking trained on expert-labelled MRI literature.
- Citation export and Zotero integration.
- Hosted dashboard for digest review and analysis comparison.
- Staging deployment connected to managed PostgreSQL, secret rotation, and production monitoring.

## Employer-Facing Review

For an ML engineer, the project shows deterministic feature extraction, interpretable scoring, golden evaluation, and strict model-output validation. For a data scientist, it shows reproducible metrics, provenance, and honest limitations. For a research software engineer, it shows modular boundaries, migrations, tests, and data integrity. For a medical-imaging R&D engineer, it keeps MRI/CVR domain logic inspectable and separates literature triage from clinical claims. For an applied AI engineer, it demonstrates how to place an LLM behind contracts, repair policy, evidence gates, and offline tests.
