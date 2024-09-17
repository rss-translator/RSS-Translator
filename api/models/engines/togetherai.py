from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from api.models.core import OpenAIInterface

class TogetherAI(OpenAIInterface):
    # https://platform.moonshot.cn/docs/api-reference
    base_url = mapped_column(URLType, default="https://api.together.xyz/v1", nullable=False, use_existing_column=True)
    # help_text="More models can be found at https://docs.together.ai/docs/inference-models#chat-models",

    __mapper_args__ = {
        'polymorphic_identity': "Together AI"
    }
