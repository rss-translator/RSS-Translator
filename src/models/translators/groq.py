from src.models.core import OpenAIInterface

class Groq(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = "https://api.groq.com/openai/v1"
    
    __mapper_args__ = {
        'polymorphic_identity': 'Groq'
    }