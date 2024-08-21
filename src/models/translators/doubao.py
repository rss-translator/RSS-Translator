from src.models.core import OpenAIInterface

class Doubao(OpenAIInterface):
    # https://www.volcengine.com/docs/82379/1262901
    base_url = "https://open.volcengineapi.com/v1"
    
    __mapper_args__ = {
        'polymorphic_identity': 'Doubao'
    }
