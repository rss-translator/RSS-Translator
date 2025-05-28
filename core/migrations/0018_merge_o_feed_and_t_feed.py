# Manual created on 2025-05-27 16:10
from django.db import migrations
import uuid
from django.conf import settings
from utils.back_db import backup_db



def merge_feeds_data(apps, schema_editor):
    """
    将O_Feed和T_Feed的数据合并到Feed模型中
    """
    # 获取历史模型
    O_Feed = apps.get_model('core', 'O_Feed')
    T_Feed = apps.get_model('core', 'T_Feed')
    Feed = apps.get_model('core', 'Feed')
    
    # 1. 处理有T_Feed的O_Feed记录
    for t_feed in T_Feed.objects.all():
        o_feed = t_feed.o_feed
        sid = uuid.uuid5(
            uuid.NAMESPACE_URL, 
            f"{o_feed.feed_url}:{t_feed.language}:{settings.SECRET_KEY}"
        ).hex
        # 创建新的Feed记录
        Feed.objects.create(
            # 基本信息从O_Feed复制
            sid=sid,
            feed_url=o_feed.feed_url,
            translation_display=o_feed.translation_display,
            etag=o_feed.etag,
            fetch=o_feed.valid,  # O_Feed.valid -> Feed.fetch
            update_frequency=o_feed.update_frequency,
            max_posts=o_feed.max_posts,
            quality=o_feed.quality,
            fetch_article=o_feed.fetch_article,
            summary_detail=o_feed.summary_detail,
            additional_prompt=o_feed.additional_prompt,
            category=o_feed.category,
            
            # 翻译器和摘要引擎的GenericForeignKey
            translator_content_type=o_feed.content_type,
            translator_object_id=o_feed.object_id,
            summary_content_type=o_feed.content_type_summary,
            summary_object_id=o_feed.object_id_summary,
            
            # 语言和翻译相关信息从T_Feed复制
            target_language=t_feed.language,
            translation_status=t_feed.status,
            translate_title=t_feed.translate_title,
            translate_content=t_feed.translate_content,
            summary=t_feed.summary,
            total_tokens=t_feed.total_tokens,
            total_characters=t_feed.total_characters,
            
            # 时间戳
            last_translate=t_feed.modified,
            last_fetch=o_feed.last_pull,
            
            # 大小信息
            size=o_feed.size + t_feed.size,
            
            # URL slug
            slug=t_feed.sid if t_feed.sid else None,
        )

            
class Migration(migrations.Migration):
    
    dependencies = [
        ('core', '0017_alter_o_feed_content_type_tagulous_feed_category_and_more'),
    ]

    
    operations = [
        migrations.RunPython(backup_db),
        migrations.RunPython(
            merge_feeds_data,
            migrations.RunPython.noop,
        ),
    ]
