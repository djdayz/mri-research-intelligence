from tests.unit.analysis.helpers import make_chunk

from mrinsight.analysis import AnalysisFocus, EvidenceSelectionService
from mrinsight.papers import SectionType


def test_methods_focus_prefers_methods_evidence() -> None:
    methods = make_chunk(
        chunk_id=1,
        section=SectionType.METHODS,
        sequence_number=1,
        text="Methods used BOLD MRI with CVR acquisition at 3 T.",
    )
    results = make_chunk(
        chunk_id=2,
        section=SectionType.RESULTS,
        sequence_number=2,
        text="Results reported a modest signal change.",
    )
    selector = EvidenceSelectionService(
        focus=AnalysisFocus.METHODS,
        max_prompt_tokens=200,
    )

    selected = selector.select((results, methods))

    assert selected.chunks[0].section_type is SectionType.METHODS


def test_references_are_excluded() -> None:
    reference = make_chunk(
        chunk_id=1,
        section=SectionType.REFERENCES,
        sequence_number=1,
        text="References 1. Example MRI paper.",
    )
    methods = make_chunk(
        chunk_id=2,
        section=SectionType.METHODS,
        sequence_number=2,
        text="Methods used MRI acquisition.",
    )
    selector = EvidenceSelectionService(max_prompt_tokens=200)

    selected = selector.select((reference, methods))

    assert selected.chunks == (methods,)


def test_results_focus_retains_results_evidence() -> None:
    methods = make_chunk(
        chunk_id=1,
        section=SectionType.METHODS,
        sequence_number=1,
        text="Methods used BOLD MRI.",
    )
    results = make_chunk(
        chunk_id=2,
        section=SectionType.RESULTS,
        sequence_number=2,
        text="Results showed CVR increased by 2.5 units.",
    )
    selector = EvidenceSelectionService(
        focus=AnalysisFocus.RESULTS,
        max_prompt_tokens=200,
    )

    selected = selector.select((methods, results))

    assert any(chunk.section_type is SectionType.RESULTS for chunk in selected.chunks)


def test_prompt_budget_is_respected() -> None:
    long_text = "MRI " * 200
    first = make_chunk(chunk_id=1, sequence_number=1, text=long_text)
    second = make_chunk(chunk_id=2, sequence_number=2, text=long_text)
    selector = EvidenceSelectionService(max_prompt_tokens=20)

    selected = selector.select((first, second))

    assert len(selected.chunks) == 1
    assert selected.estimated_tokens > selected.prompt_budget


def test_selection_ordering_and_checksum_are_deterministic() -> None:
    first = make_chunk(
        chunk_id=1,
        sequence_number=1,
        text="Methods used MRI acquisition.",
    )
    second = make_chunk(
        chunk_id=2,
        section=SectionType.RESULTS,
        sequence_number=2,
        text="Results showed CVR increased by 2.5 units.",
    )
    selector = EvidenceSelectionService(max_prompt_tokens=200)

    selected_a = selector.select((second, first))
    selected_b = selector.select((first, second))

    assert selected_a.chunks == selected_b.chunks
    assert selected_a.selection_checksum == selected_b.selection_checksum
