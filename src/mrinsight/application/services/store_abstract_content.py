from dataclasses import dataclass
from enum import StrEnum

from mrinsight.nlp import (
    TEXT_CLEANER_VERSION,
    clean_scientific_text,
    compute_text_checksum,
)
from mrinsight.papers.content import (
    ContentType,
    ExtractionStatus,
)
from mrinsight.papers.content_records import (
    NewPaperContent,
    StoredPaperContent,
)
from mrinsight.papers.repositories import (
    PaperContentRepository,
)


class ContentWriteOutcome(StrEnum):
    """Outcome of storing one scientific-content record."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class StoreAbstractContentResult:
    """Result of storing a paper abstract."""

    content: StoredPaperContent | None
    outcome: ContentWriteOutcome


class StoreAbstractContentService:
    """Clean and persist one paper's abstract evidence."""

    def __init__(
        self,
        repository: PaperContentRepository,
    ) -> None:
        self._repository = repository

    def execute(
        self,
        paper_id: int,
        abstract: str | None,
    ) -> StoreAbstractContentResult:
        """Create, update or reuse cleaned abstract content."""

        if abstract is None or not abstract.strip():
            return StoreAbstractContentResult(
                content=None,
                outcome=ContentWriteOutcome.SKIPPED,
            )

        cleaned_text = clean_scientific_text(abstract)
        checksum = compute_text_checksum(cleaned_text)

        existing = self._repository.get_by_paper_and_type(
            paper_id,
            ContentType.ABSTRACT,
        )

        if existing is None:
            created = self._repository.add(
                NewPaperContent(
                    paper_id=paper_id,
                    content_type=ContentType.ABSTRACT,
                    extraction_status=(ExtractionStatus.SUCCEEDED),
                    extracted_text=cleaned_text,
                    parser_version=TEXT_CLEANER_VERSION,
                    checksum=checksum,
                )
            )

            return StoreAbstractContentResult(
                content=created,
                outcome=ContentWriteOutcome.CREATED,
            )

        if (
            existing.extraction_status is ExtractionStatus.SUCCEEDED
            and existing.extracted_text == cleaned_text
            and existing.checksum == checksum
            and existing.parser_version == TEXT_CLEANER_VERSION
        ):
            return StoreAbstractContentResult(
                content=existing,
                outcome=ContentWriteOutcome.UNCHANGED,
            )

        updated = self._repository.update_extraction(
            existing.id,
            extraction_status=ExtractionStatus.SUCCEEDED,
            extracted_text=cleaned_text,
            parser_version=TEXT_CLEANER_VERSION,
            checksum=checksum,
        )

        return StoreAbstractContentResult(
            content=updated,
            outcome=ContentWriteOutcome.UPDATED,
        )
