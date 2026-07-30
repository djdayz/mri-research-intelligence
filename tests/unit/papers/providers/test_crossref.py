from collections.abc import Callable

import httpx
import pytest

from mrinsight.papers.providers import (
    BibliographicProviderUnavailableError,
    BibliographicRecordNotFoundError,
    CrossrefBibliographicProvider,
    InvalidBibliographicResponseError,
)


def make_crossref_payload(
    **message_overrides: object,
) -> dict[str, object]:
    """Create a representative Crossref singleton response."""

    message: dict[str, object] = {
        "DOI": "10.1234/MRI.EXAMPLE",
        "title": ["Deep Learning for MRI Reconstruction"],
        "abstract": "An MRI reconstruction study.",
        "container-title": ["Journal of MRI Research"],
        "published-online": {"date-parts": [[2026, 3, 15]]},
        "URL": ("https://doi.org/10.1234/mri.example"),
        "author": [
            {
                "given": "Alice",
                "family": "Smith",
            },
            {
                "name": "MRI Research Consortium",
            },
        ],
    }

    message.update(message_overrides)

    return {
        "status": "ok",
        "message-type": "work",
        "message-version": "1.0.0",
        "message": message,
    }


def make_provider(
    handler: Callable[
        [httpx.Request],
        httpx.Response,
    ],
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 0,
    sleeper: Callable[[float], None] = lambda _: None,
) -> tuple[
    CrossrefBibliographicProvider,
    httpx.Client,
]:
    """Create a provider backed by HTTPX MockTransport."""

    transport = httpx.MockTransport(handler)
    client = httpx.Client(
        transport=transport,
        follow_redirects=True,
    )

    provider = CrossrefBibliographicProvider(
        client=client,
        mailto="researcher@example.com",
        user_agent="MRInsight/0.1",
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        sleeper=sleeper,
    )

    return provider, client


def test_crossref_provider_resolves_metadata() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == ("/works/10.1234/mri.example")
        assert request.url.params["mailto"] == ("researcher@example.com")
        assert request.headers["user-agent"] == (
            "MRInsight/0.1 (mailto:researcher@example.com)"
        )
        assert request.headers["accept"] == "application/json"

        return httpx.Response(
            status_code=200,
            json=make_crossref_payload(),
        )

    provider, client = make_provider(handler)

    try:
        metadata = provider.resolve_by_doi("https://doi.org/10.1234/MRI.EXAMPLE")
    finally:
        client.close()

    assert metadata.doi == "10.1234/mri.example"
    assert metadata.title == ("Deep Learning for MRI Reconstruction")
    assert metadata.journal == ("Journal of MRI Research")
    assert metadata.authors == (
        "Alice Smith",
        "MRI Research Consortium",
    )
    assert metadata.publication_date is not None
    assert metadata.publication_date.isoformat() == ("2026-03-15")
    assert metadata.provider_name == "crossref"


def test_crossref_provider_maps_404_to_not_found() -> None:
    request_count = 0

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            status_code=404,
            json={"status": "not-found"},
        )

    provider, client = make_provider(handler)

    try:
        with pytest.raises(BibliographicRecordNotFoundError):
            provider.resolve_by_doi("10.1234/missing")
    finally:
        client.close()

    assert request_count == 1


def test_crossref_provider_retries_transport_failure() -> None:
    request_count = 0
    sleep_delays: list[float] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectTimeout(
                "Simulated timeout.",
                request=request,
            )

        return httpx.Response(
            status_code=200,
            json=make_crossref_payload(),
        )

    provider, client = make_provider(
        handler,
        max_attempts=2,
        backoff_seconds=0.25,
        sleeper=sleep_delays.append,
    )

    try:
        metadata = provider.resolve_by_doi("10.1234/mri.example")
    finally:
        client.close()

    assert metadata.doi == "10.1234/mri.example"
    assert request_count == 2
    assert sleep_delays == [0.25]


def test_crossref_provider_rejects_malformed_json() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=b"not-json",
            headers={"content-type": "application/json"},
        )

    provider, client = make_provider(handler)

    try:
        with pytest.raises(InvalidBibliographicResponseError):
            provider.resolve_by_doi("10.1234/mri.example")
    finally:
        client.close()


def test_crossref_provider_rejects_missing_title() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json=make_crossref_payload(title=[]),
        )

    provider, client = make_provider(handler)

    try:
        with pytest.raises(
            InvalidBibliographicResponseError,
            match="does not contain a title",
        ):
            provider.resolve_by_doi("10.1234/mri.example")
    finally:
        client.close()


def test_crossref_provider_does_not_invent_date_precision() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json=make_crossref_payload(
                **{"published-online": {"date-parts": [[2026]]}}
            ),
        )

    provider, client = make_provider(handler)

    try:
        metadata = provider.resolve_by_doi("10.1234/mri.example")
    finally:
        client.close()

    assert metadata.publication_date is None


def test_crossref_provider_stops_after_max_attempts() -> None:
    request_count = 0
    sleep_delays: list[float] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(status_code=503)

    provider, client = make_provider(
        handler,
        max_attempts=3,
        backoff_seconds=0.1,
        sleeper=sleep_delays.append,
    )

    try:
        with pytest.raises(
            BibliographicProviderUnavailableError,
            match="3 attempts",
        ):
            provider.resolve_by_doi("10.1234/mri.example")
    finally:
        client.close()

    assert request_count == 3
    assert sleep_delays == [0.1, 0.2]


def test_crossref_provider_rejects_wrong_message_type() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "status": "ok",
                "message-type": "works-list",
                "message": {"DOI": "10.1234/mri.example", "title": ["Example"]},
            },
        )

    provider, client = make_provider(handler)

    try:
        with pytest.raises(
            InvalidBibliographicResponseError,
            match="unexpected response envelope",
        ):
            provider.resolve_by_doi("10.1234/mri.example")
    finally:
        client.close()
