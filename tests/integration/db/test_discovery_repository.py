from datetime import date

import pytest
from sqlalchemy.orm import Session

from mrinsight.db.repositories import SqlAlchemyDiscoveryRepository
from mrinsight.discovery import (
    DeliveryStatus,
    DigestCadence,
    DigestPaper,
    DigestStatus,
    DiscoveryCandidate,
    DiscoveryCandidateStatus,
    DiscoveryRunStatus,
    NewSubscription,
)


@pytest.mark.integration
def test_seeded_topics_are_available(
    db_session: Session,
) -> None:
    repository = SqlAlchemyDiscoveryRepository(db_session)

    topics = repository.list_topics()

    assert len(topics) >= 7
    assert "mri-cvr-mapping" in {topic.slug for topic in topics}


@pytest.mark.integration
def test_repository_persists_subscription_run_candidate_digest_and_delivery(
    db_session: Session,
) -> None:
    repository = SqlAlchemyDiscoveryRepository(db_session)
    topic = repository.list_topics()[0]
    subscription = repository.add_subscription(
        NewSubscription(
            name="Weekly MRI CVR",
            discovery_query="MRI CVR",
            topic_ids=(topic.id,),
            minimum_relevance_score=0.2,
            preferred_categories=("mri", "cvr"),
            digest_cadence=DigestCadence.WEEKLY,
        )
    )
    run = repository.add_discovery_run(
        subscription_id=subscription.id,
        topic_id=topic.id,
        provider="fake",
        query="MRI CVR",
        from_publication_date=date(2026, 1, 1),
        until_publication_date=date(2026, 1, 31),
    )
    completed = repository.complete_discovery_run(
        run.id,
        status=DiscoveryRunStatus.SUCCEEDED,
        error=None,
    )
    candidate = repository.add_discovery_candidate(
        run_id=run.id,
        candidate=DiscoveryCandidate(
            title="BOLD MRI CVR",
            doi="10.1234/discovered",
            abstract="CVR with MRI.",
            journal="Journal",
            publication_date=date(2026, 1, 2),
            source_url="https://example.org",
            authors=("Ada Lovelace",),
            provider_name="fake",
            provider_record_id="10.1234/discovered",
        ),
        normalized_doi="10.1234/discovered",
        normalized_title="bold mri cvr",
        status=DiscoveryCandidateStatus.INGESTED,
        paper_id=None,
        relevance_score=0.9,
        rank_position=1,
        outcome_reason="created",
    )
    digest_paper = DigestPaper(
        paper_id=1,
        doi="10.1234/discovered",
        title="BOLD MRI CVR",
        journal="Journal",
        publication_date=date(2026, 1, 2),
        relevance_score=0.9,
        analysis_scope="abstract_only",
        concise_summary="Summary",
        methodology_highlights=("Methods",),
        main_results=("Results",),
        limitations=("Limitations",),
        link="https://doi.org/10.1234/discovered",
        provenance="fake",
        ranking_explanation="score",
    )
    digest = repository.add_digest(
        subscription_id=subscription.id,
        topic_id=topic.id,
        digest_date=date(2026, 1, 31),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status=DigestStatus.GENERATED,
        title="Digest",
        plain_text="Digest",
        html="<html></html>",
        selected_papers=(digest_paper,),
        error=None,
    )
    delivery = repository.add_delivery(
        digest_id=digest.id,
        provider="fake",
        destination=None,
        status=DeliveryStatus.SUCCEEDED,
        idempotency_key="test-delivery-key",
        error=None,
    )

    assert subscription.topics[0].id == topic.id
    assert completed.status is DiscoveryRunStatus.SUCCEEDED
    assert candidate.rank_position == 1
    assert repository.get_digest(digest.id) == digest
    assert delivery.status is DeliveryStatus.SUCCEEDED
