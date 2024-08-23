from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from src.models.core import OpenAIInterface

class OpenRouterAI(OpenAIInterface):
    # https://openrouter.ai/docs
    base_url = mapped_column(URLType, default="https://openrouter.ai/api/v1", nullable=False, use_existing_column=True)
    # help_text="More models can be found at https://openrouter.ai/docs#models"
    
    __mapper_args__ = {
        'polymorphic_identity': 'OpenRouter AI'
    }
