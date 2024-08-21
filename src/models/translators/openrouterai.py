from src.models.core import OpenAIInterface

class OpenRouterAI(OpenAIInterface):
    # https://openrouter.ai/docs
    base_url = "https://openrouter.ai/api/v1"
    # help_text="More models can be found at https://openrouter.ai/docs#models"
    
    __mapper_args__ = {
        'polymorphic_identity': 'Groq'
    }
