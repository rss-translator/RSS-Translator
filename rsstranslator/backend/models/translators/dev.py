import logging
from time import sleep

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import mapped_column
from rsstranslator.backend.models.core import OpenAIInterface


class TestEngine(OpenAIInterface):
    translated_text = Column(String, default="@@Translated Text@@",nullable=False)
    interval = mapped_column(Integer, nullable=False, use_existing_column=True, default=5)

    __mapper_args__ = {
        'polymorphic_identity': 'Test Engine'
    }

    def validate(self) -> bool:
        return True

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> Test Translate [%s]: %s", target_language, text)
        sleep(self.interval or 0)
        return {"text": self.translated_text, "tokens": 0, "characters": len(text)}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Test Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language)
