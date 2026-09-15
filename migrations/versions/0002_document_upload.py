"""Ajouter le statut et la taille des documents importés."""

import sqlalchemy as sa
from alembic import op

revision = "0002_document_upload"
down_revision = "0001_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "status", sa.String(13), nullable=False, server_default="METADATA_ONLY"
        ),
    )
    op.add_column("documents", sa.Column("size_bytes", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'DELETING')",
    )
    op.create_check_constraint("documents_positive_size", "documents", "size_bytes > 0")


def downgrade() -> None:
    op.drop_constraint("documents_positive_size", "documents", type_="check")
    op.drop_constraint("document_status", "documents", type_="check")
    op.drop_column("documents", "size_bytes")
    op.drop_column("documents", "status")
