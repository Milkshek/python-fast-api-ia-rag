"""Persister le texte extrait par page et le résultat d'extraction."""

import sqlalchemy as sa
from alembic import op

revision = "0003_document_pages"
down_revision = "0002_document_upload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'DELETING', 'EXTRACTED', 'FAILED')",
    )
    op.add_column(
        "documents", sa.Column("extraction_error", sa.String(40), nullable=True)
    )
    op.create_table(
        "document_pages",
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("page_number", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint("page_number > 0", name="document_pages_positive_number"),
    )


def downgrade() -> None:
    op.drop_table("document_pages")
    op.drop_column("documents", "extraction_error")
    op.execute(
        "UPDATE documents SET status = 'UPLOADED' WHERE status IN ('EXTRACTED', 'FAILED')"
    )
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'DELETING')",
    )
