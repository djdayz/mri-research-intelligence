from datetime import UTC, date, datetime

from mrinsight.discovery import DigestPaper, DigestStatus, StoredDigest
from mrinsight.discovery.delivery import (
    FakeDigestDeliveryProvider,
    render_digest_html,
    render_digest_plain_text,
)


def make_digest_paper() -> DigestPaper:
    """Return paper with text that must be escaped in HTML."""

    return DigestPaper(
        paper_id=1,
        doi="10.1234/example",
        title="<MRI & CVR>",
        journal="Journal <A>",
        publication_date=date(2026, 1, 1),
        relevance_score=0.9,
        analysis_scope="abstract_only",
        concise_summary="A <summary> & result.",
        methodology_highlights=("BOLD <MRI>",),
        main_results=("CVR increased & improved.",),
        limitations=("Abstract-only <limit>.",),
        link="https://doi.org/10.1234/example",
        provenance="fake provider",
        ranking_explanation="ranked first",
    )


def test_html_renderer_escapes_untrusted_text() -> None:
    html = render_digest_html(
        title="Digest <Preview>",
        papers=(make_digest_paper(),),
    )

    assert "&lt;MRI &amp; CVR&gt;" in html
    assert "<MRI & CVR>" not in html
    assert "&lt;summary&gt;" in html


def test_plain_text_renderer_includes_digest_fields() -> None:
    text = render_digest_plain_text(
        title="Digest Preview",
        papers=(make_digest_paper(),),
    )

    assert "Digest Preview" in text
    assert "10.1234/example" in text
    assert "BOLD <MRI>" in text


def test_fake_delivery_records_digest() -> None:
    provider = FakeDigestDeliveryProvider()
    digest = StoredDigest(
        id=1,
        idempotency_key="digest-test",
        subscription_id=1,
        topic_id=1,
        digest_date=date(2026, 1, 1),
        period_start=date(2025, 12, 25),
        period_end=date(2026, 1, 1),
        status=DigestStatus.GENERATED,
        title="Digest",
        plain_text="Digest",
        html="<html></html>",
        selected_papers=(make_digest_paper(),),
        error=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = provider.deliver(digest, destination="memory")

    assert result.succeeded is True
    assert provider.deliveries == [digest]
