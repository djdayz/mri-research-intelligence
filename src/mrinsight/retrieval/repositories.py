from typing import Protocol

from mrinsight.retrieval.records import (
    ContentRetrievalSummary,
    PageRequest,
    PaperChunkSearchResult,
    PaperSearchFilters,
    PaperSearchResult,
    PaperSort,
)


class PaperRetrievalRepository(Protocol):
    """Read-only paper search and retrieval contract."""

    def search_papers(
        self,
        *,
        filters: PaperSearchFilters,
        page: PageRequest,
        sort: PaperSort,
    ) -> PaperSearchResult:
        """Return one bounded page of paper summaries."""

    def get_paper_detail(
        self,
        paper_id: int,
    ) -> PaperSearchResult:
        """Return one paper detail result with abstract included."""

    def list_contents(
        self,
        paper_id: int,
    ) -> tuple[ContentRetrievalSummary, ...] | None:
        """Return content metadata for one paper, or None when missing."""

    def search_chunks(
        self,
        *,
        paper_id: int,
        content_id: int | None,
        section: str | None,
        page: PageRequest,
    ) -> PaperChunkSearchResult | None:
        """Return explicit chunk text for one paper, or None when missing."""
