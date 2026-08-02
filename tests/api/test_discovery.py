from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mrinsight.api.dependencies import (
    get_db_session,
    get_digest_delivery_provider,
    get_discovery_provider,
)
from mrinsight.discovery import (
    DigestDeliveryProvider,
    DiscoveryCandidate,
    DiscoveryProvider,
    FakeDigestDeliveryProvider,
    FakeDiscoveryProvider,
)
from mrinsight.main import app


@pytest.fixture
def discovery_client(
    db_session: Session,
) -> Iterator[TestClient]:
    """Create API client with fake discovery and delivery providers."""

    discovery_provider = FakeDiscoveryProvider(
        (
            DiscoveryCandidate(
                title="BOLD MRI CVR mapping",
                doi="10.1234/discovery.api",
                abstract=(
                    "BOLD MRI measured cerebrovascular reactivity. "
                    "Methods used MRI and CVR mapping. Results reported 2.5 units."
                ),
                journal="Journal of MRI Research",
                publication_date=date(2026, 1, 2),
                source_url="https://example.org/discovery-api",
                authors=("Alice Smith",),
                provider_name="fake-discovery",
                provider_record_id="10.1234/discovery.api",
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

    def override_discovery_provider() -> DiscoveryProvider:
        return discovery_provider

    def override_delivery_provider() -> DigestDeliveryProvider:
        return delivery_provider

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_discovery_provider] = override_discovery_provider
    app.dependency_overrides[get_digest_delivery_provider] = override_delivery_provider

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_subscription_digest_preview_workflow(
    discovery_client: TestClient,
) -> None:
    topics = discovery_client.get("/topics")

    assert topics.status_code == 200
    topic_id = topics.json()[0]["id"]

    created = discovery_client.post(
        "/subscriptions",
        json={
            "name": "Weekly MRI CVR",
            "discovery_query": "MRI CVR",
            "topic_ids": [topic_id],
            "minimum_relevance_score": 0,
            "preferred_categories": ["mri", "cvr"],
            "digest_cadence": "weekly",
        },
    )

    assert created.status_code == 201
    subscription_id = created.json()["id"]

    listed = discovery_client.get("/subscriptions")
    preview = discovery_client.post(
        f"/subscriptions/{subscription_id}/digest-preview",
        json={
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "rows": 5,
        },
    )

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == subscription_id
    assert preview.status_code == 201

    body = preview.json()

    assert body["candidate_count"] == 1
    assert body["delivery_status"] == "succeeded"
    assert body["digest"]["selected_papers"][0]["doi"] == "10.1234/discovery.api"
    assert "BOLD MRI CVR mapping" in body["digest"]["plain_text"]
    assert "&lt;" not in body["digest"]["html"]

    digest = discovery_client.get(f"/digests/{body['digest']['id']}")

    assert digest.status_code == 200
    assert digest.json()["id"] == body["digest"]["id"]


@pytest.mark.integration
def test_digest_preview_returns_404_for_missing_subscription(
    discovery_client: TestClient,
) -> None:
    response = discovery_client.post(
        "/subscriptions/999999/digest-preview",
        json={},
    )

    assert response.status_code == 404
