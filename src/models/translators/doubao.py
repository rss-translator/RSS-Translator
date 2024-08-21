from sqlalchemy.orm import mapped_column
from sqlalchemy_utils import URLType
from src.models.core import OpenAIInterface

class Doubao(OpenAIInterface):
    # https://www.volcengine.com/docs/82379/1262901
    base_url = mapped_column(URLType, default="https://open.volcengineapi.com/v1", nullable=False, use_existing_column=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'Doubao'
    }
