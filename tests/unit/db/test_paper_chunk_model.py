from sqlalchemy import CheckConstraint, Table, UniqueConstraint

from mrinsight.db.models import PaperChunk


def paper_chunk_table() -> Table:
    table = PaperChunk.__table__

    assert isinstance(table, Table)

    return table


def test_paper_chunk_contains_expected_columns() -> None:
    expected_columns = {
        "id",
        "paper_id",
        "paper_content_id",
        "section",
        "heading",
        "sequence_number",
        "text",
        "start_char",
        "end_char",
        "paragraph_start_sequence",
        "paragraph_end_sequence",
        "token_count",
        "page_number",
        "end_page_number",
        "chunker_version",
        "created_at",
        "updated_at",
    }

    assert set(paper_chunk_table().columns.keys()) == expected_columns


def test_paper_chunk_has_sequence_unique_constraint() -> None:
    names = {
        constraint.name
        for constraint in paper_chunk_table().constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_paper_chunks_paper_content_id_sequence_number" in names


def test_paper_chunk_has_evidence_constraints() -> None:
    names = {
        constraint.name
        for constraint in paper_chunk_table().constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_paper_chunks_supported_section",
        "ck_paper_chunks_positive_sequence",
        "ck_paper_chunks_valid_character_range",
        "ck_paper_chunks_valid_paragraph_range",
        "ck_paper_chunks_positive_token_count",
        "ck_paper_chunks_valid_page_range",
        "ck_paper_chunks_nonempty_text",
    }.issubset(names)
