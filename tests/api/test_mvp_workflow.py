from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from sqlalchemy.orm import Session

from mrinsight.analysis import FakeLLMMode, FakeLLMProvider, LLMProvider
from mrinsight.api.dependencies import (
    get_bibliographic_provider,
    get_db_session,
    get_digest_delivery_provider,
    get_discovery_provider,
    get_llm_provider,
)
from mrinsight.discovery import (
    DigestDeliveryProvider,
    DiscoveryCandidate,
    DiscoveryProvider,
    FakeDigestDeliveryProvider,
    FakeDiscoveryProvider,
)
from mrinsight.main import app
from mrinsight.papers import ResolvedPaperMetadata
from mrinsight.papers.providers import (
    BibliographicProvider,
    FakeBibliographicProvider,
)


@pytest.fixture
def mvp_client(
    db_session: Session,
) -> Iterator[TestClient]:
    metadata_provider = FakeBibliographicProvider(
        [
            ResolvedPaperMetadata(
                doi="10.1234/mvp.e2e",
                title="BOLD MRI cerebrovascular reactivity workflow",
                abstract=(
                    "BOLD MRI measured cerebrovascular reactivity. "
                    "Methods used MRI and CVR mapping. Results reported 2.5 units."
                ),
                journal="Journal of MRI Research",
                publication_date=date(2026, 4, 1),
                source_url=HttpUrl("https://example.org/papers/mvp-e2e"),
                authors=("Alice Smith", "Bob Jones"),
                provider_name="fake",
                provider_record_id="record-mvp-e2e",
            )
        ]
    )
    llm_provider = FakeLLMProvider(mode=FakeLLMMode.VALID)
    discovery_provider = FakeDiscoveryProvider(
        (
            DiscoveryCandidate(
                title="Discovery BOLD MRI CVR mapping",
                doi="10.1234/mvp.discovery",
                abstract=(
                    "Cerebrovascular reactivity was measured with BOLD MRI. "
                    "Methods included CVR mapping and results reported 2.5 units."
                ),
                journal="Journal of MRI Research",
                publication_date=date(2026, 4, 2),
                source_url="https://example.org/discovery/mvp",
                authors=("Charlie Patel",),
                provider_name="fake-discovery",
                provider_record_id="record-mvp-discovery",
            ),
        )
    )
    delivery_provider = FakeDigestDeliveryProvider()

    def override_db_session() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    def override_metadata_provider() -> BibliographicProvider:
        return metadata_provider

    def override_llm_provider() -> LLMProvider:
        return llm_provider

    def override_discovery_provider() -> DiscoveryProvider:
        return discovery_provider

    def override_delivery_provider() -> DigestDeliveryProvider:
        return delivery_provider

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_bibliographic_provider] = override_metadata_provider
    app.dependency_overrides[get_llm_provider] = override_llm_provider
    app.dependency_overrides[get_discovery_provider] = override_discovery_provider
    app.dependency_overrides[get_digest_delivery_provider] = override_delivery_provider

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_mvp_public_api_workflow(
    mvp_client: TestClient,
) -> None:
    created_paper = mvp_client.post(
        "/papers",
        json={"doi": "10.1234/MVP.E2E"},
    )
    assert created_paper.status_code == 201
    paper_id = created_paper.json()["id"]

    relevance = mvp_client.post(f"/papers/{paper_id}/relevance")
    assert relevance.status_code == 201
    assert relevance.json()["rule_label"] in {"high", "medium"}

    analysis = mvp_client.post(f"/papers/{paper_id}/analysis")
    assert analysis.status_code == 201
    analysis_body = analysis.json()
    assert analysis_body["status"] == "succeeded"
    assert analysis_body["evidence_references"]
    assert analysis_body["analysis"]["analysis_scope"] == "abstract_only"

    analysis_id = analysis_body["id"]
    assert mvp_client.get(f"/analyses/{analysis_id}").json()["id"] == analysis_id
    assert mvp_client.get(f"/papers/{paper_id}/analysis").json()[0]["id"] == analysis_id

    paper_detail = mvp_client.get(f"/papers/{paper_id}")
    chunk_list = mvp_client.get(f"/papers/{paper_id}/chunks")
    assert paper_detail.status_code == 200
    assert chunk_list.status_code == 200
    assert chunk_list.json()["items"][0]["id"] in {
        reference["chunk_id"] for reference in analysis_body["evidence_references"]
    }

    topics = mvp_client.get("/topics")
    assert topics.status_code == 200
    topic_id = topics.json()[0]["id"]

    subscription = mvp_client.post(
        "/subscriptions",
        json={
            "name": "MVP workflow digest",
            "discovery_query": "MRI CVR",
            "topic_ids": [topic_id],
            "minimum_relevance_score": 0,
            "preferred_categories": ["mri", "cvr"],
            "digest_cadence": "weekly",
        },
    )
    assert subscription.status_code == 201
    subscription_id = subscription.json()["id"]

    digest_preview = mvp_client.post(
        f"/subscriptions/{subscription_id}/digest-preview",
        json={
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "rows": 5,
        },
    )
    assert digest_preview.status_code == 201
    digest_body = digest_preview.json()
    assert digest_body["candidate_count"] == 1
    assert digest_body["delivery_status"] == "succeeded"
    assert digest_body["digest"]["idempotency_key"].startswith("digest-preview:")
    selected = digest_body["digest"]["selected_papers"][0]
    assert selected["doi"] == "10.1234/mvp.discovery"
    assert selected["concise_summary"] == (
        "The paper studies MRI evidence using supplied chunks."
    )
    assert selected["main_results"] == [
        "The paper studies MRI evidence using supplied chunks."
    ]
    assert selected["limitations"] == [
        "No limitations were reported in the supplied evidence."
    ]

    digest = mvp_client.get(f"/digests/{digest_body['digest']['id']}")
    assert digest.status_code == 200
    assert digest.json()["id"] == digest_body["digest"]["id"]
