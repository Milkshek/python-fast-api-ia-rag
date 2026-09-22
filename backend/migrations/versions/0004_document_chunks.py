"""Conserver les chunks et leur position exacte dans une page."""

import sqlalchemy as sa
from alembic import op

revision = "0004_document_chunks"
down_revision = "0003_document_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'DELETING', 'EXTRACTED', 'FAILED', 'CHUNKED')",
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "page_number"],
            ["document_pages.document_id", "document_pages.page_number"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("document_id", "chunk_index", name="document_chunks_order"),
        sa.CheckConstraint("chunk_index > 0", name="document_chunks_positive_index"),
        sa.CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset",
            name="document_chunks_offsets",
        ),
        sa.CheckConstraint(
            "char_length(text) = end_offset - start_offset",
            name="document_chunks_text_length",
        ),
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.execute("UPDATE documents SET status = 'EXTRACTED' WHERE status = 'CHUNKED'")
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'DELETING', 'EXTRACTED', 'FAILED')",
    )
