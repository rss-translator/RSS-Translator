from time import sleep
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from sqlalchemy import Column, Integer
from src.models.core import OpenAIInterface


class GeminiTranslator(OpenAIInterface):
    # https://ai.google.dev/tutorials/python_quickstart
    interval = Column(Integer, default=3)

    __mapper_args__ = {
        'polymorphic_identity': 'Google Gemini'
    }
    
    @property
    def client(self, system_prompt: str = None):
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(
            model_name=self.model,
            # system_instruction=system_prompt or self.translate_prompt
        )

    def validate(self) -> bool:
        if self.api_key:
            try:
                res = self.client.generate_content("hi")
                return res.candidates[0].finish_reason == 1
            except Exception as e:
                logging.error("GeminiTranslator validate ->%s", e)
            return False

    def translate(
        self,
        text: str,
        target_language: str,
        system_prompt: str = None,
        user_prompt: str = None,
        text_type: str = "title",
        **kwargs
    ) -> dict:
        logging.info(">>> Gemini Translate [%s]:", target_language)

        tokens = 0
        translated_text = ""
        system_prompt = (
            system_prompt or self.translate_prompt
            if text_type == "title"
            else self.content_translate_prompt
        )
        prompt = f"{system_prompt.replace('{target_language}', target_language)}\n{user_prompt}\n{text}"
        try:
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                max_output_tokens=self.max_tokens,
            )
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
            res = self.client.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
            finish_reason = res.candidates[0].finish_reason if res.candidates else None
            if finish_reason == 1:
                translated_text = res.text
            else:
                translated_text = ""
                logging.info(
                    "GeminiTranslator finish_reason->%s: %s", finish_reason.name, text
                )
            tokens = self.client.count_tokens(prompt).total_tokens
        except Exception as e:
            logging.error("GeminiTranslator->%s: %s", e, text)
        finally:
            sleep(self.interval)

        return {"text": translated_text, "tokens": tokens}

    def summarize(self, text: str, target_language: str) -> dict:
        logging.info(">>> Gemini Summarize [%s]: %s", target_language, text)
        return self.translate(text, target_language, system_prompt=self.summary_prompt)
