from src.models.core import OpenAIInterface

class TogetherAIT(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = "https://api.together.xyz/v1"
    # help_text="More models can be found at https://docs.together.ai/docs/inference-models#chat-models",

    __mapper_args__ = {
        'polymorphic_identity': "Together AI"
    }
