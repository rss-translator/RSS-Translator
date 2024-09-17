import logging
from langdetect import detect
from time import sleep
from sqlalchemy import Integer
from sqlalchemy_utils import URLType
from sqlalchemy.orm import mapped_column
from api.models.core import Engine


class FreeTranslators(Engine):
    proxy = mapped_column(URLType, nullable=True, use_existing_column=True)
    max_characters = mapped_column(Integer, nullable=False, use_existing_column=True, default=5000)
    interval = mapped_column(Integer, nullable=False, use_existing_column=True, default=5)
    
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
            text=text, dest_lang=target_language, src_lang=source_language, proxies=self.proxy
        )
        
        translated_text = (
            results.get("translated_text") if results.get("status") == "success" else ""
        )
        sleep(self.interval or 0)
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
