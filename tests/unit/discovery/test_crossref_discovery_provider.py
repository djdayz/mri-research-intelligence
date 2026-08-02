from datetime import date

import httpx
import pytest

from mrinsight.discovery import (
    CrossrefDiscoveryProvider,
    DiscoveryProviderUnavailableError,
    DiscoverySearchRequest,
)


def test_crossref_discovery_provider_searches_date_window() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "message": {
                    "items": [
                        {
                            "DOI": "10.1234/DISCOVERY",
                            "title": ["BOLD MRI CVR"],
                            "abstract": "CVR with MRI.",
                            "container-title": ["Journal"],
                            "published-print": {"date-parts": [[2026, 1, 2]]},
                            "URL": "https://example.org/work",
                            "author": [{"given": "Ada", "family": "Lovelace"}],
                            "score": 12.5,
                        }
                    ]
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = CrossrefDiscoveryProvider(
        client=client,
        mailto="test@example.org",
        user_agent="MRInsightTests/1.0",
        sleeper=lambda _delay: None,
    )

    result = provider.search(
        DiscoverySearchRequest(
            topic_query="MRI CVR",
            from_publication_date=date(2026, 1, 1),
            until_publication_date=date(2026, 1, 31),
            rows=5,
            offset=10,
        )
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].doi == "10.1234/discovery"
    assert result.candidates[0].publication_date == date(2026, 1, 2)
    assert seen_requests
    params = dict(seen_requests[0].url.params)
    assert params["query.bibliographic"] == "MRI CVR"
    assert "from-pub-date:2026-01-01" in params["filter"]
    assert params["rows"] == "5"
    assert params["offset"] == "10"


def test_crossref_discovery_provider_retries_transport_errors() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("offline")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = CrossrefDiscoveryProvider(
        client=client,
        mailto="test@example.org",
        user_agent="MRInsightTests/1.0",
        max_attempts=2,
        sleeper=lambda _delay: None,
    )

    with pytest.raises(DiscoveryProviderUnavailableError):
        provider.search(
            DiscoverySearchRequest(
                topic_query="MRI",
                from_publication_date=date(2026, 1, 1),
                until_publication_date=date(2026, 1, 31),
                rows=1,
            )
        )

    assert attempts == 2
