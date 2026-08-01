from sqlalchemy import select
from sqlalchemy.orm import Session

from mrinsight.db.models import Paper
from mrinsight.papers.records import NewPaper, StoredPaper


class SqlAlchemyPaperRepository:
    """Persist and retrieve papers using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        paper_id: int,
    ) -> StoredPaper | None:
        """Return a paper by database identity."""

        model = self._session.get(
            Paper,
            paper_id,
        )

        if model is None:
            return None

        return self._to_stored_paper(model)

    def get_by_normalized_doi(
        self,
        normalized_doi: str,
    ) -> StoredPaper | None:
        """Return a paper matching the canonical DOI."""

        statement = select(Paper).where(Paper.normalized_doi == normalized_doi)

        model = self._session.execute(statement).scalar_one_or_none()

        if model is None:
            return None

        return self._to_stored_paper(model)

    def add(
        self,
        paper: NewPaper,
    ) -> StoredPaper:
        """Add a paper and flush it without committing."""

        model = Paper(
            doi=paper.doi,
            normalized_doi=paper.normalized_doi,
            title=paper.title,
            normalized_title=paper.normalized_title,
            abstract=paper.abstract,
            journal=paper.journal,
            publication_date=paper.publication_date,
            source_url=paper.source_url,
            ingestion_source=paper.ingestion_source,
            provider_record_id=paper.provider_record_id,
        )

        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        return self._to_stored_paper(model)

    @staticmethod
    def _to_stored_paper(
        model: Paper,
    ) -> StoredPaper:
        """Translate a SQLAlchemy model into an application value."""

        return StoredPaper(
            id=model.id,
            doi=model.doi,
            normalized_doi=model.normalized_doi,
            title=model.title,
            normalized_title=model.normalized_title,
            abstract=model.abstract,
            journal=model.journal,
            publication_date=model.publication_date,
            source_url=model.source_url,
            ingestion_source=model.ingestion_source,
            provider_record_id=model.provider_record_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
