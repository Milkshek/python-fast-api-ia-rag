import pytest
from sqlalchemy import delete

from app.database.session import SessionFactory, engine
from app.documents.models import Document


@pytest.fixture(autouse=True)
def clean_test_database():
    # Protection contre un lancement accidentel avec les paramètres de développement.
    assert engine.url.database == "document_intelligence_test"
    assert engine.url.host == "db-test"
    with SessionFactory.begin() as session:
        session.execute(delete(Document))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(Document))
