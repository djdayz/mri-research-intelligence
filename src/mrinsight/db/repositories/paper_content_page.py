from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mrinsight.db.models import PaperContentPage
from mrinsight.papers import (
    NewPaperContentPage,
    StoredPaperContentPage,
)


class SqlAlchemyPaperContentPageRepository:
    """Persist text-bearing PDF pages using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_content(
        self,
        paper_content_id: int,
    ) -> tuple[StoredPaperContentPage, ...]:
        """Return text-bearing pages in page order."""

        statement = (
            select(PaperContentPage)
            .where(PaperContentPage.paper_content_id == paper_content_id)
            .order_by(PaperContentPage.page_number)
        )

        models = self._session.execute(statement).scalars()

        return tuple(self._to_record(model) for model in models)

    def replace_for_content(
        self,
        paper_content_id: int,
        pages: Sequence[NewPaperContentPage],
    ) -> tuple[StoredPaperContentPage, ...]:
        """Replace all text-bearing pages for one content record."""

        self._session.execute(
            delete(PaperContentPage).where(
                PaperContentPage.paper_content_id == paper_content_id
            )
        )

        models = [
            PaperContentPage(
                paper_content_id=paper_content_id,
                page_number=page.page_number,
                text=page.text,
                start_char=page.start_char,
                end_char=page.end_char,
            )
            for page in pages
        ]

        self._session.add_all(models)
        self._session.flush()

        for model in models:
            self._session.refresh(model)

        return tuple(self._to_record(model) for model in models)

    @staticmethod
    def _to_record(
        model: PaperContentPage,
    ) -> StoredPaperContentPage:
        """Translate an ORM model into an application record."""

        return StoredPaperContentPage(
            id=model.id,
            paper_content_id=model.paper_content_id,
            page_number=model.page_number,
            text=model.text,
            start_char=model.start_char,
            end_char=model.end_char,
            created_at=model.created_at,
        )
