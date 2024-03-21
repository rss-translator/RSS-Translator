1. add languages to settings.py
```
LANGUAGES = [
    ('en', 'English'),
    ('zh-hans', '简体中文'),
]
```

2. create django.po file
`django-admin makemessages -l zh_Hans`

3. open po file and start translate to target language

4. compile po to mo file for django
`django-admin compilemessages`