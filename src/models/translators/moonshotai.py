from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from src.models.core import OpenAIInterface

class MoonshotAI(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = mapped_column(URLType, default="https://api.moonshot.cn/v1", nullable=False, use_existing_column=True)
    
    __mapper_args__ = {
        'polymorphic_identity': "Moonshot AI"
    }
