from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mrinsight.db.base import Base


class LLMRun(Base):
    """One LLM provider request sequence."""

    __tablename__ = "llm_runs"

    __table_args__ = (
        CheckConstraint(
            "request_status IN ('succeeded', 'failed', 'provider_failed')",
            name="ck_llm_runs_supported_request_status",
        ),
        CheckConstraint(
            "repair_attempt_count >= 0",
            name="ck_llm_runs_nonnegative_repair_attempts",
        ),
        CheckConstraint(
            "input_token_count IS NULL OR input_token_count >= 0",
            name="ck_llm_runs_nonnegative_input_tokens",
        ),
        CheckConstraint(
            "output_token_count IS NULL OR output_token_count >= 0",
            name="ck_llm_runs_nonnegative_output_tokens",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_llm_runs_nonnegative_latency",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_llm_runs_nonnegative_estimated_cost",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_chunk_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    request_status: Mapped[str] = mapped_column(String(32), nullable=False)
    repair_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
