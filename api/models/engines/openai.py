from api.models.core import OpenAIInterface

class OpenAI(OpenAIInterface):
    # https://platform.openai.com/docs/api-reference/chat
    __mapper_args__ = {
        'polymorphic_identity': 'OpenAI'
    }
