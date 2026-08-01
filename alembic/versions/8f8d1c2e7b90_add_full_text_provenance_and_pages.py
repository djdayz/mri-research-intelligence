"""add full text provenance and pages

Revision ID: 8f8d1c2e7b90
Revises: bf951eb60f80
Create Date: 2026-07-31 15:42:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f8d1c2e7b90"
down_revision: str | Sequence[str] | None = "bf951eb60f80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "paper_contents",
        sa.Column("source_filename", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column("source_media_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column("source_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column("access_basis", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column("text_page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column("extractor_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "paper_contents",
        sa.Column(
            "extractor_library_version",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "paper_contents",
        sa.Column("extraction_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_paper_contents_source_sha256",
        "paper_contents",
        ["source_sha256"],
        unique=False,
    )

    op.execute(
        "UPDATE paper_contents "
        "SET extraction_error = 'Historical extraction failure.' "
        "WHERE extraction_status = 'failed' "
        "AND extraction_error IS NULL"
    )

    op.drop_constraint(
        "ck_paper_contents_successful_content_has_text",
        "paper_contents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_paper_contents_valid_extraction_state",
        "paper_contents",
        "("
        "extraction_status = 'succeeded' "
        "AND extracted_text IS NOT NULL "
        "AND checksum IS NOT NULL "
        "AND extraction_error IS NULL"
        ") OR ("
        "extraction_status = 'failed' "
        "AND extracted_text IS NULL "
        "AND checksum IS NULL "
        "AND extraction_error IS NOT NULL"
        ")",
    )
    op.create_check_constraint(
        "ck_paper_contents_supported_access_basis",
        "paper_contents",
        "access_basis IS NULL OR access_basis IN ('user_upload', 'open_access')",
    )
    op.create_check_constraint(
        "ck_paper_contents_valid_source_sha256",
        "paper_contents",
        "source_sha256 IS NULL OR length(source_sha256) = 64",
    )
    op.create_check_constraint(
        "ck_paper_contents_positive_page_count",
        "paper_contents",
        "page_count IS NULL OR page_count >= 1",
    )
    op.create_check_constraint(
        "ck_paper_contents_nonnegative_text_page_count",
        "paper_contents",
        "text_page_count IS NULL OR text_page_count >= 0",
    )
    op.create_check_constraint(
        "ck_paper_contents_valid_text_page_count",
        "paper_contents",
        "page_count IS NULL "
        "OR text_page_count IS NULL "
        "OR text_page_count <= page_count",
    )
    op.create_check_constraint(
        "ck_paper_contents_full_text_has_provenance",
        "paper_contents",
        "content_type != 'full_text' OR ("
        "source_filename IS NOT NULL "
        "AND source_media_type IS NOT NULL "
        "AND source_sha256 IS NOT NULL "
        "AND access_basis IS NOT NULL "
        "AND page_count IS NOT NULL "
        "AND text_page_count IS NOT NULL "
        "AND extractor_name IS NOT NULL "
        "AND extractor_library_version IS NOT NULL"
        ")",
    )

    op.add_column(
        "paper_chunks",
        sa.Column("end_page_number", sa.Integer(), nullable=True),
    )
    op.drop_constraint(
        "ck_paper_chunks_positive_page_number",
        "paper_chunks",
        type_="check",
    )
    op.create_check_constraint(
        "ck_paper_chunks_valid_page_range",
        "paper_chunks",
        "("
        "page_number IS NULL "
        "AND end_page_number IS NULL"
        ") OR ("
        "page_number >= 1 "
        "AND end_page_number >= page_number"
        ")",
    )

    op.create_table(
        "paper_content_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_content_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_char > start_char AND start_char >= 0",
            name="ck_paper_content_pages_valid_character_range",
        ),
        sa.CheckConstraint(
            "length(text) > 0",
            name="ck_paper_content_pages_nonempty_text",
        ),
        sa.CheckConstraint(
            "page_number >= 1",
            name="ck_paper_content_pages_positive_page_number",
        ),
        sa.ForeignKeyConstraint(
            ["paper_content_id"],
            ["paper_contents.id"],
            name=op.f("fk_paper_content_pages_paper_content_id_paper_contents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_content_pages")),
        sa.UniqueConstraint(
            "paper_content_id",
            "page_number",
            name="uq_paper_content_pages_content_id_page_number",
        ),
    )
    op.create_index(
        op.f("ix_paper_content_pages_paper_content_id"),
        "paper_content_pages",
        ["paper_content_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_paper_content_pages_paper_content_id"),
        table_name="paper_content_pages",
    )
    op.drop_table("paper_content_pages")

    op.drop_constraint(
        "ck_paper_chunks_valid_page_range",
        "paper_chunks",
        type_="check",
    )
    op.create_check_constraint(
        "ck_paper_chunks_positive_page_number",
        "paper_chunks",
        "page_number IS NULL OR page_number >= 1",
    )
    op.drop_column("paper_chunks", "end_page_number")

    op.drop_constraint(
        "ck_paper_contents_full_text_has_provenance",
        "paper_contents",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_contents_valid_text_page_count",
        "paper_contents",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_contents_nonnegative_text_page_count",
        "paper_contents",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_contents_positive_page_count",
        "paper_contents",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_contents_valid_source_sha256",
        "paper_contents",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_contents_supported_access_basis",
        "paper_contents",
        type_="check",
    )
    op.drop_constraint(
        "ck_paper_contents_valid_extraction_state",
        "paper_contents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_paper_contents_successful_content_has_text",
        "paper_contents",
        "(extraction_status = 'succeeded' "
        "AND extracted_text IS NOT NULL "
        "AND checksum IS NOT NULL) "
        "OR extraction_status = 'failed'",
    )
    op.drop_index(
        "ix_paper_contents_source_sha256",
        table_name="paper_contents",
    )
    op.drop_column("paper_contents", "extraction_error")
    op.drop_column("paper_contents", "extractor_library_version")
    op.drop_column("paper_contents", "extractor_name")
    op.drop_column("paper_contents", "text_page_count")
    op.drop_column("paper_contents", "page_count")
    op.drop_column("paper_contents", "access_basis")
    op.drop_column("paper_contents", "source_sha256")
    op.drop_column("paper_contents", "source_media_type")
    op.drop_column("paper_contents", "source_filename")
