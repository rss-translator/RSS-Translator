import logging
from langdetect import detect
from time import sleep
from sqlalchemy import Column, Integer
from sqlalchemy_utils import URLType
from src.models.core import Engine


class FreeTranslators(Engine):
    proxy = Column(URLType, nullable=True)
    max_characters = Column(Integer, default=5000)
    interval = Column(Integer, default=5)
    
    __mapper_args__ = {
        'polymorphic_identity': "Free Translators"
    }

    @property
    def client(self):
        from easytranslator import EasyTranslator
        return EasyTranslator(translators=[])

    def validate(self) -> bool:
        return True

    def translate(self, text: str, target_language: str, source_language:str="auto", **kwargs) -> dict:
        try:
            source_language = detect(text) if source_language == "auto" else source_language
        except:
            source_language = "auto"
            logging.warning("Cannot detect source language:%s", text)
            
        results = self.client.translate(
            text=text, dest_lang=target_language, src_lang=source_language, proxies=self.proxies
        )
        
        translated_text = (
            results.get("translated_text") if results.get("status") == "success" else ""
        )
        sleep(self.interval)
        return {"text": translated_text, "characters": len(text)}

    def translate_batch(self, text_list: list, target_language: str, **kwargs) -> dict:
        pass
        return {}
        """
        {
            original_text: {
                "translated_text": "...",
                "status": "success" / "error"
                "error_info": error info if got error
            }
        }
        """
