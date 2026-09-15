from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.database.session import SessionFactory, engine
from app.documents.models import Document
from app.documents.status import DocumentStatus


def test_existing_document_survives_upload_migration():
    config = Config("alembic.ini")
    identifier = uuid4()
    command.downgrade(config, "0001_documents")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO documents (id, title, filename) VALUES (:id, 'Ancien', 'a.pdf')"
                ),
                {"id": identifier},
            )
    finally:
        command.upgrade(config, "head")
    with SessionFactory() as session:
        document = session.get(Document, identifier)
        assert document is not None
        assert document.title == "Ancien"
        assert document.status == DocumentStatus.METADATA_ONLY
        assert document.size_bytes is None
