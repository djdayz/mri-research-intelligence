from collections.abc import Sequence
from typing import Protocol

from mrinsight.papers.content_page_records import (
    NewPaperContentPage,
    StoredPaperContentPage,
)


class PaperContentPageRepository(Protocol):
    """Persistence contract for extracted PDF pages."""

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperContentPage, ...]:
        """Return text-bearing pages in page order."""

        ...

    def replace_for_content(
        self,
        paper_content_id: int,
        pages: Sequence[NewPaperContentPage],
    ) -> tuple[StoredPaperContentPage, ...]:
        """Atomically replace one content record's pages."""

        ...
