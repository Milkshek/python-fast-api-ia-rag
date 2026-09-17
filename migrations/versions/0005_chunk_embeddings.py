"""Vecteurs de chunks et identité de leur modèle."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0005_chunk_embeddings"
down_revision = "0004_document_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "documents", sa.Column("embedding_generation", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("embedding_model", sa.String(100), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("embedding_dimensions", sa.Integer(), nullable=True)
    )
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'EXTRACTED', 'FAILED', 'DELETING', 'CHUNKED', 'INDEXED')",
    )
    op.create_table(
        "chunk_embeddings",
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("vector", Vector(768), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chunk_embeddings")
    op.execute("UPDATE documents SET status = 'CHUNKED' WHERE status = 'INDEXED'")
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('METADATA_ONLY', 'UPLOADED', 'EXTRACTED', 'FAILED', 'DELETING', 'CHUNKED')",
    )
    op.drop_column("documents", "embedding_dimensions")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "embedding_generation")
    # L'extension peut être partagée avec d'autres tables : ne pas la supprimer.
