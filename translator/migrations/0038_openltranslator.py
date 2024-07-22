# Generated by Django 5.0.6 on 2024-07-22 02:11

import encrypted_model_fields.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('translator', '0037_doubaotranslator'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpenlTranslator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Name')),
                ('valid', models.BooleanField(null=True, verbose_name='Valid')),
                ('is_ai', models.BooleanField(default=False, editable=False)),
                ('api_key', encrypted_model_fields.fields.EncryptedCharField()),
                ('url', models.URLField(default='https://api.openl.club', max_length=255)),
                ('service_name', models.CharField(default='deepl', help_text='Please get it from https://docs.openl.club/#/API/format?id=%e7%bf%bb%e8%af%91%e6%9c%8d%e5%8a%a1%e4%bb%a3%e7%a0%81%e5%90%8d', max_length=50, verbose_name='Translate Service Name')),
                ('max_characters', models.IntegerField(default=5000)),
            ],
            options={
                'verbose_name': 'Openl',
                'verbose_name_plural': 'Openl',
            },
        ),
    ]
