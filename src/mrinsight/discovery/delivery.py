import re
import smtplib
import time
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from html import escape
from pathlib import Path
from typing import Any, Protocol

from mrinsight.discovery.records import DigestPaper, StoredDigest


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Provider-independent delivery result."""

    provider: str
    destination: str | None
    succeeded: bool
    error: str | None = None
    provider_response_id: str | None = None
    attempt_count: int = 1
    retryable: bool = False


class DigestDeliveryProvider(Protocol):
    """Delivery-provider contract for digest previews."""

    @property
    def name(self) -> str:
        """Return provider name."""

    def deliver(
        self,
        digest: StoredDigest,
        *,
        destination: str | None,
    ) -> DeliveryResult:
        """Deliver or preview one digest."""


class ConsoleDigestDeliveryProvider:
    """Write digest plain text to stdout."""

    @property
    def name(self) -> str:
        """Return provider name."""

        return "console"

    def deliver(
        self,
        digest: StoredDigest,
        *,
        destination: str | None,
    ) -> DeliveryResult:
        """Print digest plain text."""

        del destination
        print(digest.plain_text)
        return DeliveryResult(
            provider=self.name,
            destination=None,
            succeeded=True,
        )


class FileDigestDeliveryProvider:
    """Write digest HTML and plain-text files to a directory."""

    def __init__(
        self,
        output_dir: Path,
    ) -> None:
        self._output_dir = output_dir

    @property
    def name(self) -> str:
        """Return provider name."""

        return "file"

    def deliver(
        self,
        digest: StoredDigest,
        *,
        destination: str | None,
    ) -> DeliveryResult:
        """Write digest preview files."""

        output_dir = Path(destination) if destination is not None else self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"digest-{digest.id}"
        text_path = output_dir / f"{stem}.txt"
        html_path = output_dir / f"{stem}.html"
        text_path.write_text(digest.plain_text, encoding="utf-8")
        html_path.write_text(digest.html, encoding="utf-8")

        return DeliveryResult(
            provider=self.name,
            destination=str(output_dir),
            succeeded=True,
            provider_response_id=f"{text_path.name}:{html_path.name}",
        )


class FakeDigestDeliveryProvider:
    """Deterministic delivery provider for offline tests."""

    def __init__(self) -> None:
        self.deliveries: list[StoredDigest] = []
        self.failures_before_success = 0

    @property
    def name(self) -> str:
        """Return provider name."""

        return "fake-delivery"

    def deliver(
        self,
        digest: StoredDigest,
        *,
        destination: str | None,
    ) -> DeliveryResult:
        """Record delivery without side effects."""

        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            return DeliveryResult(
                provider=self.name,
                destination=destination,
                succeeded=False,
                error="Simulated retryable fake delivery failure.",
                retryable=True,
            )

        self.deliveries.append(digest)
        return DeliveryResult(
            provider=self.name,
            destination=destination,
            succeeded=True,
            provider_response_id=f"fake-delivery-{digest.id}",
        )


@dataclass(frozen=True, slots=True)
class SmtpDigestDeliveryConfig:
    """Configuration for SMTP digest delivery."""

    host: str
    port: int
    sender: str
    username: str | None
    password: str | None
    use_tls: bool
    use_ssl: bool
    timeout_seconds: float
    max_attempts: int
    backoff_seconds: float


class SmtpDigestDeliveryProvider:
    """Deliver digest previews through an SMTP server."""

    def __init__(
        self,
        config: SmtpDigestDeliveryConfig,
        *,
        smtp_factory: Callable[..., Any] | None = None,
        smtp_ssl_factory: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._smtp_factory = smtp_factory or smtplib.SMTP
        self._smtp_ssl_factory = smtp_ssl_factory or smtplib.SMTP_SSL
        self._sleep = sleep

    @property
    def name(self) -> str:
        """Return provider name."""

        return "smtp"

    def deliver(
        self,
        digest: StoredDigest,
        *,
        destination: str | None,
    ) -> DeliveryResult:
        """Send one digest email with bounded retries."""

        recipient = _validated_email(destination or "")
        sender = _validated_email(self._config.sender)

        if recipient is None:
            return DeliveryResult(
                provider=self.name,
                destination=destination,
                succeeded=False,
                error="Invalid recipient email address.",
            )
        if sender is None:
            return DeliveryResult(
                provider=self.name,
                destination=recipient,
                succeeded=False,
                error="Invalid SMTP sender email address.",
            )

        message_id = make_msgid()
        message = _build_email_message(
            digest=digest,
            sender=sender,
            recipient=recipient,
            message_id=message_id,
        )
        last_error: str | None = None
        retryable = True
        attempt = 1

        for attempt in range(1, self._config.max_attempts + 1):
            try:
                refused = self._send_message(message)
            except Exception as error:
                last_error = _smtp_error_message(error)
                retryable = _is_retryable_smtp_error(error)
            else:
                if not refused:
                    return DeliveryResult(
                        provider=self.name,
                        destination=recipient,
                        succeeded=True,
                        provider_response_id=message_id,
                        attempt_count=attempt,
                    )
                last_error = "SMTP server refused one or more recipients."
                retryable = False

            if not retryable or attempt == self._config.max_attempts:
                break
            if self._config.backoff_seconds > 0:
                self._sleep(self._config.backoff_seconds)

        return DeliveryResult(
            provider=self.name,
            destination=recipient,
            succeeded=False,
            error=last_error or "SMTP delivery failed.",
            provider_response_id=message_id,
            attempt_count=attempt,
            retryable=retryable,
        )

    def _send_message(
        self,
        message: EmailMessage,
    ) -> dict[str, tuple[int, bytes]]:
        smtp_factory = (
            self._smtp_ssl_factory if self._config.use_ssl else self._smtp_factory
        )
        with smtp_factory(
            self._config.host,
            self._config.port,
            timeout=self._config.timeout_seconds,
        ) as smtp:
            if self._config.use_tls and not self._config.use_ssl:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
            if self._config.username is not None:
                smtp.login(self._config.username, self._config.password or "")
            return smtp.send_message(message)


def render_digest_plain_text(
    *,
    title: str,
    papers: tuple[DigestPaper, ...],
) -> str:
    """Render digest as plain text."""

    lines = [title, "=" * len(title), ""]
    if not papers:
        lines.append("No papers matched this subscription period.")
        return "\n".join(lines)

    for index, paper in enumerate(papers, start=1):
        relevance = (
            str(paper.relevance_score)
            if paper.relevance_score is not None
            else "not scored"
        )
        methods = "; ".join(paper.methodology_highlights) or "not reported"
        results = "; ".join(paper.main_results) or "not reported"
        limitations = "; ".join(paper.limitations) or "not reported"
        lines.extend(
            [
                f"{index}. {paper.title}",
                f"   DOI: {paper.doi or 'not available'}",
                f"   Journal: {paper.journal or 'not reported'}",
                f"   Publication date: {paper.publication_date or 'not reported'}",
                f"   Relevance: {relevance}",
                f"   Scope: {paper.analysis_scope or 'not available'}",
                f"   Summary: {paper.concise_summary}",
                f"   Methods: {methods}",
                f"   Results: {results}",
                f"   Limitations: {limitations}",
                f"   Link: {paper.link or 'not available'}",
                f"   Provenance: {paper.provenance}",
                f"   Ranking: {paper.ranking_explanation}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def render_digest_html(
    *,
    title: str,
    papers: tuple[DigestPaper, ...],
) -> str:
    """Render digest as sanitized HTML."""

    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{escape(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape(title)}</h1>",
    ]

    if not papers:
        parts.append("<p>No papers matched this subscription period.</p>")
    else:
        parts.append("<ol>")
        for paper in papers:
            publication_date = str(paper.publication_date or "not reported")
            relevance = (
                str(paper.relevance_score)
                if paper.relevance_score is not None
                else "not scored"
            )
            doi = escape(paper.doi or "not available")
            journal = escape(paper.journal or "not reported")
            scope = escape(paper.analysis_scope or "not available")
            link = escape(paper.link or "not available")
            parts.extend(
                [
                    "<li>",
                    f"<h2>{escape(paper.title)}</h2>",
                    f"<p><strong>DOI:</strong> {doi}</p>",
                    f"<p><strong>Journal:</strong> {journal}</p>",
                    (
                        "<p><strong>Publication date:</strong> "
                        f"{escape(publication_date)}</p>"
                    ),
                    f"<p><strong>Relevance:</strong> {escape(relevance)}</p>",
                    f"<p><strong>Scope:</strong> {scope}</p>",
                    f"<p>{escape(paper.concise_summary)}</p>",
                    _html_list("Methodology highlights", paper.methodology_highlights),
                    _html_list("Main results", paper.main_results),
                    _html_list("Limitations", paper.limitations),
                    f"<p><strong>Link:</strong> {link}</p>",
                    f"<p><strong>Provenance:</strong> {escape(paper.provenance)}</p>",
                    (
                        "<p><strong>Ranking:</strong> "
                        f"{escape(paper.ranking_explanation)}</p>"
                    ),
                    "</li>",
                ]
            )
        parts.append("</ol>")

    parts.extend(["</body>", "</html>"])
    return "\n".join(parts)


def _html_list(
    label: str,
    values: tuple[str, ...],
) -> str:
    """Render a sanitized labelled list."""

    if not values:
        return f"<p><strong>{escape(label)}:</strong> not reported</p>"

    items = "".join(f"<li>{escape(value)}</li>" for value in values)
    return f"<p><strong>{escape(label)}:</strong></p><ul>{items}</ul>"


def _build_email_message(
    *,
    digest: StoredDigest,
    sender: str,
    recipient: str,
    message_id: str,
) -> EmailMessage:
    """Build a multipart digest email."""

    message = EmailMessage()
    message["Subject"] = digest.title
    message["From"] = sender
    message["To"] = recipient
    message["Message-ID"] = message_id
    message.set_content(digest.plain_text)
    message.add_alternative(digest.html, subtype="html")
    return message


def _validated_email(
    value: str,
) -> str | None:
    """Return a normalized single email address, if valid enough to deliver."""

    address = value.strip()
    _, parsed = parseaddr(address)

    if parsed != address:
        return None
    if "," in address or "\n" in address or "\r" in address:
        return None
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", address) is None:
        return None
    return address


def _smtp_error_message(
    error: Exception,
) -> str:
    """Return a compact non-secret SMTP error message."""

    if isinstance(error, smtplib.SMTPResponseException):
        return f"SMTP error {error.smtp_code}."
    return type(error).__name__


def _is_retryable_smtp_error(
    error: Exception,
) -> bool:
    """Classify SMTP errors for bounded retries."""

    if isinstance(error, smtplib.SMTPResponseException):
        return 400 <= error.smtp_code < 500
    return isinstance(
        error,
        (
            TimeoutError,
            OSError,
            smtplib.SMTPConnectError,
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPDataError,
        ),
    )
