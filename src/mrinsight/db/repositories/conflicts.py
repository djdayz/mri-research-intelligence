from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

T = TypeVar("T")


class ConcurrentInsertRecoveryError(RuntimeError):
    """Raised when an insert conflict cannot be resolved by re-querying."""


def add_with_conflict_recovery(
    session: Session,
    *,
    insert: Callable[[], T],
    recover: Callable[[], T | None],
    message: str,
) -> T:
    """Run an insert in a savepoint and recover an existing row on conflict."""

    try:
        with session.begin_nested():
            return insert()
    except IntegrityError as error:
        recovered = recover()
        if recovered is None:
            raise ConcurrentInsertRecoveryError(message) from error
        return recovered
