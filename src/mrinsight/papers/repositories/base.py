from typing import Protocol

from mrinsight.papers.records import NewPaper, StoredPaper


class PaperRepository(Protocol):
    """Persistence contract required by paper use cases."""

    def get_by_id(
        self,
        paper_id: int,
    ) -> StoredPaper | None:
        """Return one paper by database identity."""

        ...

    def get_by_normalized_doi(
        self,
        normalized_doi: str,
    ) -> StoredPaper | None:
        """Return a paper with the canonical DOI, if present."""

        ...

    def add(
        self,
        paper: NewPaper,
    ) -> StoredPaper:
        """Persist a new paper without committing the transaction."""

        ...
