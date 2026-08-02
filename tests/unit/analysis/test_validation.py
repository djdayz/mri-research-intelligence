from tests.unit.analysis.helpers import make_chunk, make_content, make_paper

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    EvidenceBackedText,
    EvidenceReference,
    EvidenceRole,
    InformationStatus,
    NumericalResult,
    ResultDirection,
    ScientificPaperAnalysis,
    build_unavailable_statement,
)
from mrinsight.papers import AnalysisScope, SectionType


def make_reference(
    *,
    chunk_id: int = 3,
    section: SectionType = SectionType.METHODS,
    excerpt: str = "MRI methods",
    role: EvidenceRole = EvidenceRole.PRIMARY,
) -> EvidenceReference:
    """Create a valid-looking reference for validator tests."""

    return EvidenceReference(
        paper_id=1,
        content_id=2,
        chunk_id=chunk_id,
        section=section,
        start_page=1,
        end_page=1,
        start_char=0,
        end_char=len("MRI methods reported 2.5 units."),
        excerpt=excerpt,
        role=role,
    )


def make_analysis(
    *,
    reference: EvidenceReference | None = None,
    analysis_scope: AnalysisScope = AnalysisScope.ABSTRACT_ONLY,
    numerical_value_text: str = "2.5",
) -> ScientificPaperAnalysis:
    """Create a schema-valid analysis."""

    reference = reference or make_reference()
    numerical_reference = reference.model_copy(update={"role": EvidenceRole.NUMERICAL})
    claim = EvidenceBackedText(
        status=InformationStatus.REPORTED,
        text="The paper reports an MRI method.",
        evidence_references=(reference,),
    )
    unavailable = build_unavailable_statement("Not reported.")

    return ScientificPaperAnalysis(
        paper_id=1,
        analysis_scope=analysis_scope,
        content_id=2,
        source_checksum=make_content().checksum or "",
        objective=claim,
        study_design=unavailable,
        population_or_dataset=unavailable,
        acquisition_details=unavailable,
        preprocessing=unavailable,
        methodology_steps=(claim,),
        model_or_statistical_methods=unavailable,
        validation_design=unavailable,
        comparison_methods=unavailable,
        key_results=(claim,),
        numerical_results=(
            NumericalResult(
                metric="reported value",
                value_text=numerical_value_text,
                direction=ResultDirection.UNCERTAIN,
                evidence_reference=numerical_reference,
            ),
        ),
        strengths=(unavailable,),
        limitations=(unavailable,),
        suggested_improvements=(unavailable,),
        reproducibility_notes=(unavailable,),
        clinical_or_scientific_significance=claim,
        uncertainty=(unavailable,),
        missing_information=(unavailable,),
    )


def test_validator_accepts_valid_evidence_references() -> None:
    result = AnalysisEvidenceValidator().validate(
        analysis=make_analysis(),
        paper=make_paper(),
        content=make_content(),
        chunks=(make_chunk(),),
    )

    assert result.valid is True
    assert result.errors == ()


def test_validator_rejects_unknown_chunk_reference() -> None:
    result = AnalysisEvidenceValidator().validate(
        analysis=make_analysis(reference=make_reference(chunk_id=999)),
        paper=make_paper(),
        content=make_content(),
        chunks=(make_chunk(),),
    )

    assert result.valid is False
    assert any("unknown chunk_id" in error for error in result.errors)


def test_validator_rejects_excerpt_mismatch() -> None:
    result = AnalysisEvidenceValidator().validate(
        analysis=make_analysis(reference=make_reference(excerpt="not in chunk")),
        paper=make_paper(),
        content=make_content(),
        chunks=(make_chunk(),),
    )

    assert result.valid is False
    assert any("excerpt does not occur" in error for error in result.errors)


def test_validator_rejects_references_section_by_default() -> None:
    reference = make_reference(section=SectionType.REFERENCES)
    result = AnalysisEvidenceValidator().validate(
        analysis=make_analysis(reference=reference),
        paper=make_paper(),
        content=make_content(),
        chunks=(make_chunk(section=SectionType.REFERENCES),),
    )

    assert result.valid is False
    assert any("references-section evidence" in error for error in result.errors)


def test_validator_rejects_numerical_value_absent_from_evidence() -> None:
    result = AnalysisEvidenceValidator().validate(
        analysis=make_analysis(numerical_value_text="999"),
        paper=make_paper(),
        content=make_content(),
        chunks=(make_chunk(),),
    )

    assert result.valid is False
    assert any("value is not present" in error for error in result.errors)
