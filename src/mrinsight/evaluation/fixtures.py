from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from mrinsight.analysis import FakeLLMMode
from mrinsight.nlp import compute_text_checksum
from mrinsight.papers import (
    AnalysisScope,
    ContentType,
    ExtractionStatus,
    SectionType,
    StoredPaperChunk,
    StoredPaperContent,
)
from mrinsight.papers.records import StoredPaper


@dataclass(frozen=True, slots=True)
class GoldenEvaluationCase:
    """One legally reusable synthetic evaluation case."""

    case_id: str
    description: str
    paper: StoredPaper
    content: StoredPaperContent
    chunks: tuple[StoredPaperChunk, ...]
    analysis_scope: AnalysisScope
    fake_mode: FakeLLMMode
    expected_success: bool
    expected_repair_count: int


def load_golden_evaluation_cases() -> tuple[GoldenEvaluationCase, ...]:
    """Return synthetic cases covering safety-critical analysis behavior."""

    valid = _case(
        case_id="synthetic-valid-evidence",
        description="Valid evidence-backed abstract analysis with numerical support.",
        fake_mode=FakeLLMMode.VALID,
        expected_success=True,
        expected_repair_count=0,
    )
    repaired = _case(
        case_id="synthetic-repairable-json",
        description="Malformed first response repaired into valid structured output.",
        fake_mode=FakeLLMMode.REPAIRABLE_MALFORMED_JSON,
        expected_success=True,
        expected_repair_count=1,
    )
    missing_evidence = _case(
        case_id="synthetic-missing-evidence",
        description="Reported claims without evidence must fail validation.",
        fake_mode=FakeLLMMode.MISSING_EVIDENCE,
        expected_success=False,
        expected_repair_count=1,
    )
    numerical_mismatch = _case(
        case_id="synthetic-numerical-mismatch",
        description="Numerical claims must cite evidence containing the value.",
        fake_mode=FakeLLMMode.NUMERICAL_INCONSISTENCY,
        expected_success=False,
        expected_repair_count=1,
    )
    scope_mismatch = _case(
        case_id="synthetic-abstract-scope-mismatch",
        description="Abstract-only evidence cannot be presented as full text.",
        fake_mode=FakeLLMMode.ABSTRACT_FULL_TEXT_MISMATCH,
        expected_success=False,
        expected_repair_count=1,
    )

    return (
        valid,
        repaired,
        missing_evidence,
        numerical_mismatch,
        scope_mismatch,
    )


def _case(
    *,
    case_id: str,
    description: str,
    fake_mode: FakeLLMMode,
    expected_success: bool,
    expected_repair_count: int,
) -> GoldenEvaluationCase:
    now = datetime.now(UTC)
    text = (
        "This synthetic BOLD MRI study measured cerebrovascular reactivity. "
        "Methods used carbon dioxide challenge MRI and CVR mapping. "
        "Results reported 2.5 units of signal change, with limitations from "
        "small sample size and abstract-only evidence."
    )
    checksum = compute_text_checksum(text)
    paper = StoredPaper(
        id=101,
        doi="10.1234/synthetic-eval",
        normalized_doi="10.1234/synthetic-eval",
        title="Synthetic BOLD MRI cerebrovascular reactivity study",
        normalized_title="synthetic bold mri cerebrovascular reactivity study",
        abstract=text,
        journal="Synthetic Evaluation Journal",
        publication_date=date(2026, 5, 1),
        source_url=None,
        ingestion_source="synthetic-evaluation",
        provider_record_id=case_id,
        created_at=now,
        updated_at=now,
    )
    content = StoredPaperContent(
        id=202,
        paper_id=paper.id,
        content_type=ContentType.ABSTRACT,
        extraction_status=ExtractionStatus.SUCCEEDED,
        extracted_text=text,
        parser_version="synthetic-evaluation-v1",
        checksum=checksum,
        created_at=now,
        updated_at=now,
    )
    chunk = StoredPaperChunk(
        id=303,
        paper_id=paper.id,
        paper_content_id=content.id,
        section_type=SectionType.ABSTRACT,
        heading="Abstract",
        sequence_number=1,
        text=text,
        start_char=0,
        end_char=len(text),
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=len(text.split()),
        page_number=None,
        end_page_number=None,
        chunker_version="synthetic-evaluation-v1",
        created_at=now,
        updated_at=now,
    )

    return GoldenEvaluationCase(
        case_id=case_id,
        description=description,
        paper=paper,
        content=content,
        chunks=(chunk,),
        analysis_scope=AnalysisScope.ABSTRACT_ONLY,
        fake_mode=fake_mode,
        expected_success=expected_success,
        expected_repair_count=expected_repair_count,
    )
