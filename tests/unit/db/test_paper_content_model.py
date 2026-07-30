from sqlalchemy import CheckConstraint, String, Table, UniqueConstraint

from mrinsight.db.models import PaperContent


def paper_content_table() -> Table:
    table = PaperContent.__table__

    assert isinstance(table, Table)

    return table


def test_paper_content_contains_expected_columns() -> None:
    expected_columns = {
        "id",
        "paper_id",
        "content_type",
        "extraction_status",
        "extracted_text",
        "parser_version",
        "checksum",
        "created_at",
        "updated_at",
    }

    assert set(paper_content_table().columns.keys()) == expected_columns


def test_paper_content_has_scope_unique_constraint() -> None:
    constraint_names = {
        constraint.name
        for constraint in paper_content_table().constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_paper_contents_paper_id_content_type" in constraint_names


def test_paper_content_has_state_check_constraints() -> None:
    constraint_names = {
        constraint.name
        for constraint in paper_content_table().constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_paper_contents_supported_content_type",
        "ck_paper_contents_supported_extraction_status",
        "ck_paper_contents_successful_content_has_text",
    }.issubset(constraint_names)


def test_paper_content_checksum_has_expected_length() -> None:
    checksum_column = paper_content_table().c.checksum

    assert isinstance(checksum_column.type, String)
    assert checksum_column.type.length == 64
