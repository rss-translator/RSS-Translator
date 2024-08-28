import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rsstranslator.backend.models.translators import AzureAI
from rsstranslator.backend.models.core import Base

@pytest.fixture(scope="module")
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def azure_translator(db_session):
    translator = AzureAI(
        name="test_translator",
        api_key="test_api_key",
        base_url="https://test.openai.azure.com/",
        version="2024-02-15-preview",
        model="test_model"
    )
    db_session.add(translator)
    db_session.commit()
    return translator

def test_azure_translator_creation(azure_translator):
    assert azure_translator.api_key == "test_api_key"
    assert azure_translator.base_url == "https://test.openai.azure.com/"
    assert azure_translator.version == "2024-02-15-preview"
    assert azure_translator.model == "test_model"