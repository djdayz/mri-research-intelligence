from dataclasses import dataclass

from mrinsight.papers import (
    AnalysisScope,
    ContentType,
    ExtractionStatus,
    StoredPaperContent,
)
from mrinsight.papers.repositories import (
    PaperContentRepository,
)


class NoAnalyzableContentError(RuntimeError):
    """Raised when a paper has no successful evidence source."""


@dataclass(frozen=True, slots=True)
class SelectedAnalysisContent:
    """Content and scope selected for scientific analysis."""

    content: StoredPaperContent
    scope: AnalysisScope


class SelectAnalysisContentService:
    """Prefer successful full text, then fall back to abstract."""

    def __init__(
        self,
        repository: PaperContentRepository,
    ) -> None:
        self._repository = repository

    def execute(
        self,
        paper_id: int,
    ) -> SelectedAnalysisContent:
        full_text = self._repository.get_by_paper_and_type(
            paper_id,
            ContentType.FULL_TEXT,
        )

        if full_text is not None and _is_analyzable(full_text):
            return SelectedAnalysisContent(
                content=full_text,
                scope=AnalysisScope.FULL_TEXT,
            )

        abstract = self._repository.get_by_paper_and_type(
            paper_id,
            ContentType.ABSTRACT,
        )

        if abstract is not None and _is_analyzable(abstract):
            return SelectedAnalysisContent(
                content=abstract,
                scope=AnalysisScope.ABSTRACT_ONLY,
            )

        raise NoAnalyzableContentError(f"Paper {paper_id} has no analyzable content.")


def _is_analyzable(
    content: StoredPaperContent | None,
) -> bool:
    """Return whether content can be used for analysis."""

    return (
        content is not None
        and content.extraction_status is ExtractionStatus.SUCCEEDED
        and content.extracted_text is not None
        and content.checksum is not None
    )
