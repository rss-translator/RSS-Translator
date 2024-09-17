from sqlalchemy import Column, String
from api.models.core import OpenAIInterface

class AzureAI(OpenAIInterface):
    # https://learn.microsoft.com/azure/ai-services/openai/
    # base_url = Column(URLType, default="https://example.openai.azure.com/", nullable=False)
    version = Column(String(100), nullable=False, default="2024-02-15-preview")
    # model = Column(String(100), default="Your Deployment Name", nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'AzureAI'
    }

    @property
    def client(self):
        from openai import AzureOpenAI
        return AzureOpenAI(
            api_key=self.api_key,
            api_version=self.version,
            azure_endpoint=self.base_url,
            timeout=120.0,
        )
