from datetime import UTC, date, datetime

from mrinsight.papers import SectionType, StoredPaper, StoredPaperChunk
from mrinsight.relevance import RelevanceLabel, RuleBasedRelevanceScorer


def make_paper(
    *,
    title: str,
    abstract: str | None,
) -> StoredPaper:
    """Create a stored paper record for scoring tests."""

    now = datetime.now(tz=UTC)
    return StoredPaper(
        id=1,
        doi="10.1234/relevance",
        normalized_doi="10.1234/relevance",
        title=title,
        normalized_title=title.casefold(),
        abstract=abstract,
        journal="MRInsight Tests",
        publication_date=date(2026, 1, 1),
        source_url=None,
        ingestion_source="test",
        provider_record_id="record-1",
        created_at=now,
        updated_at=now,
    )


def make_chunk(
    *,
    text: str,
    section: SectionType,
) -> StoredPaperChunk:
    """Create a stored chunk record for scoring tests."""

    now = datetime.now(tz=UTC)
    return StoredPaperChunk(
        id=10,
        paper_id=1,
        paper_content_id=5,
        section_type=section,
        heading=None,
        sequence_number=1,
        text=text,
        start_char=0,
        end_char=len(text),
        paragraph_start_sequence=1,
        paragraph_end_sequence=1,
        token_count=len(text.split()),
        page_number=2,
        end_page_number=3,
        chunker_version="test",
        created_at=now,
        updated_at=now,
    )


def test_scorer_labels_cvr_mri_paper_high() -> None:
    scorer = RuleBasedRelevanceScorer()
    paper = make_paper(
        title="BOLD CVR mapping with MRI",
        abstract="Cerebrovascular reactivity was measured during hypercapnia.",
    )

    result = scorer.score(
        paper=paper,
        selected_text=paper.abstract or "",
        chunks=[
            make_chunk(
                text="Methods used end-tidal CO2 and 3 T fMRI.",
                section=SectionType.METHODS,
            )
        ],
    )

    assert result.label is RelevanceLabel.HIGH
    assert "cvr" in result.matched_concepts
    assert "mri_general" in result.matched_concepts
    assert result.supporting_locations[0].source == "title"


def test_scorer_rejects_unrelated_machine_learning() -> None:
    scorer = RuleBasedRelevanceScorer()
    paper = make_paper(
        title="Transformer classification for customer churn",
        abstract="A machine learning model predicts subscription cancellation.",
    )

    result = scorer.score(
        paper=paper,
        selected_text=paper.abstract or "",
        chunks=[],
    )

    assert result.label is RelevanceLabel.NOT_RELEVANT
    assert result.normalized_score == 0


def test_scorer_identifies_mri_reconstruction() -> None:
    scorer = RuleBasedRelevanceScorer()
    paper = make_paper(
        title="Unrolled network for accelerated MRI reconstruction",
        abstract="Compressed sensing and SENSE baselines were compared.",
    )

    result = scorer.score(
        paper=paper,
        selected_text=paper.abstract or "",
        chunks=[],
    )

    assert result.label in {RelevanceLabel.MEDIUM, RelevanceLabel.HIGH}
    assert "mri_reconstruction" in result.matched_concepts
    assert result.category_scores["reconstruction"] > 0
