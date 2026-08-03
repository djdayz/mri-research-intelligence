from mrinsight.db import models
from mrinsight.db.base import Base


def test_all_models_are_registered_for_alembic_metadata() -> None:
    expected_tables = {
        "digest_deliveries",
        "digests",
        "discovery_candidates",
        "discovery_runs",
        "llm_runs",
        "paper_analyses",
        "paper_chunks",
        "paper_content_pages",
        "paper_contents",
        "paper_relevance_assessments",
        "papers",
        "subscription_topics",
        "subscriptions",
        "topics",
    }

    assert expected_tables <= set(Base.metadata.tables)
    assert models.Paper.metadata is Base.metadata
