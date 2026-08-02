from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Protocol

from mrinsight.discovery.records import DigestPaper, StoredDigest


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Provider-independent delivery result."""

    provider: str
    destination: str | None
    succeeded: bool
    error: str | None = None


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
        )


class FakeDigestDeliveryProvider:
    """Deterministic delivery provider for offline tests."""

    def __init__(self) -> None:
        self.deliveries: list[StoredDigest] = []

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

        self.deliveries.append(digest)
        return DeliveryResult(
            provider=self.name,
            destination=destination,
            succeeded=True,
        )


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
