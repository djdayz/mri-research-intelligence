from sqlalchemy import Table, UniqueConstraint

from mrinsight.db.models import Paper


def test_paper_model_contains_expected_columns() -> None:
    assert isinstance(Paper.__table__, Table)

    expected_columns = {
        "id",
        "doi",
        "normalized_doi",
        "title",
        "normalized_title",
        "abstract",
        "publication_date",
        "source_url",
        "created_at",
        "updated_at",
    }

    assert set(Paper.__table__.columns.keys()) == expected_columns


def test_paper_model_has_unique_normalized_doi_constraint() -> None:
    assert isinstance(Paper.__table__, Table)

    unique_constraint_names = {
        constraint.name
        for constraint in Paper.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_papers_normalized_doi" in unique_constraint_names


def test_paper_title_is_required_and_abstract_is_optional() -> None:
    assert isinstance(Paper.__table__, Table)

    assert Paper.__table__.c.title.nullable is False
    assert Paper.__table__.c.abstract.nullable is True


def test_normalized_title_is_required_and_indexed() -> None:
    normalized_title = Paper.__table__.c.normalized_title

    assert normalized_title.nullable is False
    assert normalized_title.index is True
