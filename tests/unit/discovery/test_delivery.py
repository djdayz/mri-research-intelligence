import smtplib
from datetime import UTC, date, datetime
from typing import Any

from mrinsight.discovery import DigestPaper, DigestStatus, StoredDigest
from mrinsight.discovery.delivery import (
    FakeDigestDeliveryProvider,
    SmtpDigestDeliveryConfig,
    SmtpDigestDeliveryProvider,
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
    assert result.provider_response_id == "fake-delivery-1"


def test_smtp_delivery_sends_plain_text_and_html_message() -> None:
    sent_messages: list[Any] = []

    class RecordingSmtp:
        def __init__(
            self,
            host: str,
            port: int,
            *,
            timeout: float,
        ) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout
            self.started_tls = False
            self.logged_in = False

        def __enter__(self) -> "RecordingSmtp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def ehlo(self) -> None:
            return None

        def starttls(self) -> None:
            self.started_tls = True

        def login(
            self,
            username: str,
            password: str,
        ) -> None:
            assert username == "smtp-user"
            assert password == "smtp-password"
            self.logged_in = True

        def send_message(
            self,
            message: Any,
        ) -> dict[str, tuple[int, bytes]]:
            sent_messages.append(message)
            return {}

    provider = SmtpDigestDeliveryProvider(
        SmtpDigestDeliveryConfig(
            host="smtp.example.org",
            port=587,
            sender="sender@example.org",
            username="smtp-user",
            password="smtp-password",
            use_tls=True,
            use_ssl=False,
            timeout_seconds=5.0,
            max_attempts=2,
            backoff_seconds=0,
        ),
        smtp_factory=RecordingSmtp,
    )

    result = provider.deliver(_make_digest(), destination="reader@example.org")

    assert result.succeeded is True
    assert result.provider == "smtp"
    assert result.provider_response_id is not None
    assert result.attempt_count == 1
    assert sent_messages[0]["To"] == "reader@example.org"
    assert sent_messages[0]["From"] == "sender@example.org"
    assert sent_messages[0].is_multipart()


def test_smtp_delivery_retries_temporary_errors() -> None:
    attempts = 0

    class FlakySmtp:
        def __init__(
            self,
            host: str,
            port: int,
            *,
            timeout: float,
        ) -> None:
            del host, port, timeout

        def __enter__(self) -> "FlakySmtp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def send_message(
            self,
            message: Any,
        ) -> dict[str, tuple[int, bytes]]:
            del message
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise smtplib.SMTPDataError(451, b"try later")
            return {}

    provider = SmtpDigestDeliveryProvider(
        _smtp_config(max_attempts=3),
        smtp_factory=FlakySmtp,
    )

    result = provider.deliver(_make_digest(), destination="reader@example.org")

    assert result.succeeded is True
    assert result.attempt_count == 2


def test_smtp_delivery_rejects_invalid_recipient_without_sending() -> None:
    def fail_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError("SMTP should not be opened for invalid recipients.")

    provider = SmtpDigestDeliveryProvider(
        _smtp_config(),
        smtp_factory=fail_if_called,
    )

    result = provider.deliver(_make_digest(), destination="not an email")

    assert result.succeeded is False
    assert result.retryable is False
    assert result.error == "Invalid recipient email address."


def _make_digest() -> StoredDigest:
    return StoredDigest(
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


def _smtp_config(
    *,
    max_attempts: int = 2,
) -> SmtpDigestDeliveryConfig:
    return SmtpDigestDeliveryConfig(
        host="smtp.example.org",
        port=587,
        sender="sender@example.org",
        username=None,
        password=None,
        use_tls=False,
        use_ssl=False,
        timeout_seconds=5.0,
        max_attempts=max_attempts,
        backoff_seconds=0,
    )
