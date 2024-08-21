from src.models.core import OpenAIInterface

class MoonshotAI(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = "https://api.moonshot.cn/v1"
    
    __mapper_args__ = {
        'polymorphic_identity': "Moonshot AI"
    }
