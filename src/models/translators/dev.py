import logging
from time import sleep

from sqlalchemy import Column, Integer, String
from src.models.core import Engine


class Test(Engine):
    translated_text = Column(String, default="@@Translated Text@@",nullable=False)
    max_characters = Column(Integer, default=5000)
    interval = Column(Integer, default=3)
    is_ai = True

    __mapper_args__ = {
        'polymorphic_identity': 'Test'
    }

    def validate(self) -> bool:
        return True

    def translate(self, text: str, target_language: str, **kwargs) -> dict:
        logging.info(">>> Test Translate [%s]: %s", target_language, text)
        sleep(self.interval)
        return {"text": self.translated_text, "tokens": 0, "characters": len(text)}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Test Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language)
