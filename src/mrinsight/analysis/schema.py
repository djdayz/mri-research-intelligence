from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mrinsight.papers import AnalysisScope, SectionType

ANALYSIS_SCHEMA_VERSION = "paper-analysis-schema-v1"


class EvidenceRole(StrEnum):
    """How an evidence reference supports an analysis field."""

    PRIMARY = "primary"
    SUPPORTING = "supporting"
    LIMITATION = "limitation"
    NUMERICAL = "numerical"


class InformationStatus(StrEnum):
    """Closed status for reported and unavailable scientific information."""

    REPORTED = "reported"
    NOT_REPORTED = "not_reported"
    UNAVAILABLE_ABSTRACT_ONLY = "unavailable_abstract_only"
    UNCERTAIN = "uncertain"
    UNSUPPORTED = "unsupported"


class ResultDirection(StrEnum):
    """Direction for a numerical or comparative result."""

    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CLEAR_DIFFERENCE = "no_clear_difference"
    NOT_APPLICABLE = "not_applicable"
    UNCERTAIN = "uncertain"


class EvidenceReference(BaseModel):
    """Reference to one persisted evidence chunk."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    paper_id: int = Field(gt=0)
    content_id: int = Field(gt=0)
    chunk_id: int = Field(gt=0)
    section: SectionType
    start_page: int | None = Field(default=None, gt=0)
    end_page: int | None = Field(default=None, gt=0)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    excerpt: str | None = Field(default=None, min_length=1)
    role: EvidenceRole

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        """Ensure page and character ranges are internally coherent."""

        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char.")
        if (
            self.start_page is None
            and self.end_page is not None
            or self.start_page is not None
            and self.end_page is None
        ):
            raise ValueError("start_page and end_page must be provided together.")
        if (
            self.start_page is not None
            and self.end_page is not None
            and self.end_page < self.start_page
        ):
            raise ValueError("end_page cannot be before start_page.")

        return self


class EvidenceBackedText(BaseModel):
    """One analysis statement with explicit evidence or unavailability status."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    status: InformationStatus
    text: str = Field(min_length=1)
    evidence_references: tuple[EvidenceReference, ...] = ()

    @model_validator(mode="after")
    def require_evidence_for_reported_claims(self) -> Self:
        """Require evidence for reported or uncertain scientific claims."""

        if self.status in {
            InformationStatus.REPORTED,
            InformationStatus.UNCERTAIN,
        } and not self.evidence_references:
            raise ValueError("Reported or uncertain claims require evidence.")

        return self


class NumericalResult(BaseModel):
    """Typed numerical result with evidence attribution."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    metric: str = Field(min_length=1)
    value: float | None = None
    value_text: str | None = Field(default=None, min_length=1)
    unit: str | None = Field(default=None, min_length=1)
    direction: ResultDirection
    comparator: str | None = Field(default=None, min_length=1)
    confidence_interval: str | None = Field(default=None, min_length=1)
    uncertainty: str | None = Field(default=None, min_length=1)
    sample_size: int | None = Field(default=None, gt=0)
    evidence_reference: EvidenceReference

    @model_validator(mode="after")
    def require_value_or_text(self) -> Self:
        """Allow unparseable numerical findings as text, but not empty results."""

        if self.value is None and self.value_text is None:
            raise ValueError("Numerical results require value or value_text.")

        return self


class ScientificPaperAnalysis(BaseModel):
    """Strict versioned schema for evidence-linked scientific analysis."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    schema_version: str = ANALYSIS_SCHEMA_VERSION
    paper_id: int = Field(gt=0)
    analysis_scope: AnalysisScope
    content_id: int = Field(gt=0)
    source_checksum: str = Field(min_length=64, max_length=64)

    objective: EvidenceBackedText
    study_design: EvidenceBackedText
    population_or_dataset: EvidenceBackedText
    acquisition_details: EvidenceBackedText
    preprocessing: EvidenceBackedText
    methodology_steps: tuple[EvidenceBackedText, ...]
    model_or_statistical_methods: EvidenceBackedText
    validation_design: EvidenceBackedText
    comparison_methods: EvidenceBackedText
    key_results: tuple[EvidenceBackedText, ...]
    numerical_results: tuple[NumericalResult, ...]
    strengths: tuple[EvidenceBackedText, ...]
    limitations: tuple[EvidenceBackedText, ...]
    suggested_improvements: tuple[EvidenceBackedText, ...]
    reproducibility_notes: tuple[EvidenceBackedText, ...]
    clinical_or_scientific_significance: EvidenceBackedText
    uncertainty: tuple[EvidenceBackedText, ...]
    missing_information: tuple[EvidenceBackedText, ...]

    @model_validator(mode="after")
    def validate_schema_version(self) -> Self:
        """Reject analyses built for a different schema version."""

        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError("Unsupported analysis schema version.")

        return self


def build_unavailable_statement(
    text: str,
    *,
    status: InformationStatus = InformationStatus.NOT_REPORTED,
) -> EvidenceBackedText:
    """Create a statement for unavailable information without evidence."""

    if status in {
        InformationStatus.REPORTED,
        InformationStatus.UNCERTAIN,
    }:
        raise ValueError("Use explicit evidence for reported or uncertain claims.")

    return EvidenceBackedText(
        status=status,
        text=text,
        evidence_references=(),
    )
