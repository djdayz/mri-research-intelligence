# Portfolio Case Study

MRInsight demonstrates a research-software approach to MRI paper intelligence.

## Problem

Researchers need a reproducible way to collect, inspect, and triage MRI literature without blurring abstracts, full text, and generated interpretation.

## Engineering Choices

- Modular monolith with FastAPI, SQLAlchemy, Alembic, and PostgreSQL.
- Deterministic DOI normalization, text cleaning, section detection, chunking, and relevance before any LLM layer.
- Provider interfaces and fakes for offline tests.
- PostgreSQL-backed integration tests rather than SQLite substitutes.

## Trade-offs

- Rule-based relevance is explainable but not clinically validated.
- pypdf is practical for permitted uploads but limited for layout-heavy papers.
- The LLM, discovery, digest, Docker, and deployment layers remain future work.
