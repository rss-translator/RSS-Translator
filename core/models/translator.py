from django.db import models
from django.core.exceptions import ValidationError
from enum import Enum
import json
from encrypted_model_fields.fields import EncryptedCharField
from django.utils.translation import gettext_lazy as _

class TranslationService(Enum):
    DEEPL = 'deepl'
    OPENAI = 'openai'

class Translator(models.Model):
    SERVICE_CHOICES = [
        (TranslationService.DEEPL.value, 'DeepL'),
        (TranslationService.OPENAI.value, 'OpenAI'),
    ]

    name = models.CharField(_("Name"), max_length=100, unique=True)
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    base_url = models.CharField(_("Base URL"), max_length=255, null=True)
    api_key = EncryptedCharField(_("API Key"), max_length=255, null=True)
    valid = models.BooleanField(_("Valid"), null=True)
    is_default = models.BooleanField(_("Default"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    service_config = models.JSONField(_("Service Config"), default=dict, null=True)

    class Meta:
        verbose_name = "Translator"
        verbose_name_plural = "Translators"
        ordering = ["-is_default", "name"]
        unique_together = ("name", "service")
        indexes = [
            models.Index(fields=["service"]),
            models.Index(fields=["is_default"]),
        ]
    
    def __str__(self):
        return self.name

    def clean(self):
        """验证服务配置"""
        super().clean()
        
        # 服务特定配置验证
        if self.service == TranslationService.DEEPL.value:
            self._validate_deepl_config()
        elif self.service == TranslationService.OPENAI.value:
            self._validate_openai_config()
    
    def _validate_deepl_config(self):
        """验证DeepL配置"""
        config = self.service_config
        # 允许的DeepL配置字段
        allowed_keys = {
            'server_url', 'timeout', 
            'max_retries', 'preserve_formatting',
            'split_sentences', 'formality'
        }
        
        # 检查无效字段
        invalid_keys = set(config.keys()) - allowed_keys
        if invalid_keys:
            raise ValidationError(f"Invalid DeepL config keys: {', '.join(invalid_keys)}")
            
        if 'timeout' in config and not isinstance(config['timeout'], (int, float)):
            raise ValidationError("timeout must be a number")
    
    def _validate_openai_config(self):
        """验证OpenAI配置"""
        config = self.service_config
        # 允许的OpenAI配置字段
        allowed_keys = {
            'model', 'temperature', 'max_tokens', 'timeout',
            'top_p', 'frequency_penalty', 'presence_penalty',
            'system_prompt', 'max_retries'
        }
        
        # 检查无效字段
        invalid_keys = set(config.keys()) - allowed_keys
        if invalid_keys:
            raise ValidationError(f"Invalid OpenAI config keys: {', '.join(invalid_keys)}")
        
        # 类型验证示例
        if 'model' in config and not isinstance(config['model'], str):
            raise ValidationError("model must be a string")
            
        if 'temperature' in config and not (0 <= config['temperature'] <= 2):
            raise ValidationError("temperature must be between 0 and 2")
    
    def get_service_client(self):
        """返回配置好的翻译客户端"""
        from .clients import get_translation_client  # 避免循环导入
        
        return get_translation_client(
            service=self.service,
            api_key=self.api_key,
            **self.service_config
        )
    
    @classmethod
    def get_default_translator(cls, service=None):
        """获取默认翻译器，可指定服务类型"""
        queryset = cls.objects.filter(is_default=True)
        if service:
            queryset = queryset.filter(service=service)
        return queryset.first()
    
    def translate(self, text: str, target_language: str, source_language:str="auto", **kwargs) -> dict:
        raise NotImplementedError(
            "subclasses of Translator must provide a translate() method"
        )

    def min_size(self) -> int:
        if hasattr(self, "max_characters"):
            return self.max_characters * 0.7
        if hasattr(self, "max_tokens"):
            return self.max_tokens * 0.7
        return 0

    def max_size(self) -> int:
        if hasattr(self, "max_characters"):
            return self.max_characters * 0.9
        if hasattr(self, "max_tokens"):
            return self.max_tokens * 0.9
        return 0

    def validate(self) -> bool:
        raise NotImplementedError(
            "subclasses of Translator must provide a validate() method"
        )
