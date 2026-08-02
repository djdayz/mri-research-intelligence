from dataclasses import dataclass

from mrinsight.analysis.schema import (
    EvidenceBackedText,
    EvidenceReference,
    EvidenceRole,
    NumericalResult,
    ScientificPaperAnalysis,
)
from mrinsight.papers import AnalysisScope, SectionType, StoredPaperChunk
from mrinsight.papers.content_records import StoredPaperContent
from mrinsight.papers.records import StoredPaper


@dataclass(frozen=True, slots=True)
class AnalysisEvidenceValidationResult:
    """Outcome of validating analysis evidence references."""

    valid: bool
    errors: tuple[str, ...]


class AnalysisEvidenceValidator:
    """Validate generated analysis claims against persisted evidence chunks."""

    def validate(
        self,
        *,
        analysis: ScientificPaperAnalysis,
        paper: StoredPaper,
        content: StoredPaperContent,
        chunks: tuple[StoredPaperChunk, ...],
        allow_references_section: bool = False,
    ) -> AnalysisEvidenceValidationResult:
        """Return validation errors for unsupported or inconsistent evidence."""

        errors: list[str] = []

        if analysis.paper_id != paper.id:
            errors.append("analysis.paper_id does not match the analysed paper.")

        if analysis.content_id != content.id:
            errors.append("analysis.content_id does not match the analysed content.")

        if analysis.source_checksum != content.checksum:
            errors.append(
                "analysis.source_checksum does not match the content checksum."
            )

        if (
            content.content_type.value == "abstract"
            and analysis.analysis_scope is not AnalysisScope.ABSTRACT_ONLY
        ):
            errors.append("abstract content cannot be presented as full-text analysis.")

        chunk_by_id = {chunk.id: chunk for chunk in chunks}

        for field_name, statement in _iter_evidence_backed_statements(analysis):
            for reference in statement.evidence_references:
                errors.extend(
                    _validate_reference(
                        reference=reference,
                        chunk_by_id=chunk_by_id,
                        expected_paper_id=paper.id,
                        expected_content_id=content.id,
                        field_name=field_name,
                        allow_references_section=allow_references_section,
                    )
                )

        for index, result in enumerate(analysis.numerical_results, start=1):
            reference = result.evidence_reference
            errors.extend(
                _validate_reference(
                    reference=reference,
                    chunk_by_id=chunk_by_id,
                    expected_paper_id=paper.id,
                    expected_content_id=content.id,
                    field_name=f"numerical_results[{index}]",
                    allow_references_section=allow_references_section,
                )
            )
            if reference.role is not EvidenceRole.NUMERICAL:
                errors.append(
                    f"numerical_results[{index}] evidence role must be numerical."
                )
            chunk = chunk_by_id.get(reference.chunk_id)
            if chunk is not None and not _numeric_result_appears_in_evidence(
                result,
                chunk,
            ):
                errors.append(
                    f"numerical_results[{index}] value is not present in "
                    "cited evidence."
                )

        return AnalysisEvidenceValidationResult(
            valid=not errors,
            errors=tuple(errors),
        )


def _iter_evidence_backed_statements(
    analysis: ScientificPaperAnalysis,
) -> tuple[tuple[str, EvidenceBackedText], ...]:
    """Flatten all evidence-backed text fields with their schema paths."""

    statements: list[tuple[str, EvidenceBackedText]] = [
        ("objective", analysis.objective),
        ("study_design", analysis.study_design),
        ("population_or_dataset", analysis.population_or_dataset),
        ("acquisition_details", analysis.acquisition_details),
        ("preprocessing", analysis.preprocessing),
        ("model_or_statistical_methods", analysis.model_or_statistical_methods),
        ("validation_design", analysis.validation_design),
        ("comparison_methods", analysis.comparison_methods),
        (
            "clinical_or_scientific_significance",
            analysis.clinical_or_scientific_significance,
        ),
    ]

    for field_name in (
        "methodology_steps",
        "key_results",
        "strengths",
        "limitations",
        "suggested_improvements",
        "reproducibility_notes",
        "uncertainty",
        "missing_information",
    ):
        values = getattr(analysis, field_name)
        statements.extend(
            (f"{field_name}[{index}]", value)
            for index, value in enumerate(values, start=1)
        )

    return tuple(statements)


def _validate_reference(
    *,
    reference: EvidenceReference,
    chunk_by_id: dict[int, StoredPaperChunk],
    expected_paper_id: int,
    expected_content_id: int,
    field_name: str,
    allow_references_section: bool,
) -> tuple[str, ...]:
    """Validate one evidence reference against persisted chunks."""

    errors: list[str] = []
    chunk = chunk_by_id.get(reference.chunk_id)

    if reference.paper_id != expected_paper_id:
        errors.append(f"{field_name} references the wrong paper_id.")

    if reference.content_id != expected_content_id:
        errors.append(f"{field_name} references the wrong content_id.")

    if chunk is None:
        errors.append(f"{field_name} references unknown chunk_id {reference.chunk_id}.")
        return tuple(errors)

    if chunk.paper_id != expected_paper_id:
        errors.append(f"{field_name} chunk belongs to a different paper.")

    if chunk.paper_content_id != expected_content_id:
        errors.append(f"{field_name} chunk belongs to a different content record.")

    if reference.section is not chunk.section_type:
        errors.append(f"{field_name} section does not match the referenced chunk.")

    if reference.section is SectionType.REFERENCES and not allow_references_section:
        errors.append(f"{field_name} uses references-section evidence.")

    if reference.start_char != chunk.start_char or reference.end_char != chunk.end_char:
        errors.append(f"{field_name} character offsets do not match the chunk.")

    if reference.start_page != chunk.page_number:
        errors.append(f"{field_name} start_page does not match the chunk.")

    if reference.end_page != chunk.end_page_number:
        errors.append(f"{field_name} end_page does not match the chunk.")

    if reference.excerpt is not None and reference.excerpt not in chunk.text:
        errors.append(f"{field_name} excerpt does not occur in the referenced chunk.")

    return tuple(errors)


def _numeric_result_appears_in_evidence(
    result: NumericalResult,
    chunk: StoredPaperChunk,
) -> bool:
    """Return whether the numeric result is visible in cited evidence."""

    haystack = chunk.text.casefold()

    if result.value_text is not None:
        return result.value_text.casefold() in haystack

    if result.value is None:
        return False

    candidates = {
        str(result.value),
        f"{result.value:g}",
    }

    return any(candidate in haystack for candidate in candidates)
