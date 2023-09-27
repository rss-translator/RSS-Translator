# [RSS Translator](https://www.rsstranslator.com/)
[EN](README_EN.md) / [中文](README.md) 

RSS Translator is finally in beta after 3 months. \
Website: https://www.rsstranslator.com \
The main reason for the development is to solve personal needs, follow a lot of foreign bloggers, but the English title is not conducive to rapid screening, so I made RSS translator.

### Technology stack:
Front-end: No framework, purely hand-built (HTML+JS+CSS)\
Backend: Python\    
Front-end deployed in Cloudflare's Pages\
Backend and database deployed in Appwrite\
Translation engine: GPT-3.5 / Filtered content will be translated using DeepL

### How to use:
Open [RSS Translator](https://www.rsstranslator.com/), input the feed source address, select the target language, and click Create.

### Notes:
1.Only translate the headlines.\
2.Free of charge, if it is helpful to you, you are welcome to [Sponsor](https://github.com/sponsors/versun) to maintain the free status.\
3.Larger feeds will take longer to translate (around 5 minutes) (only the first 1000 headlines are translated) \
4.All feeds are automatically updated every 20 minutes.\
5.Re-entering the same feed on the web side will force it to update once.

It's still in beta, bugs are welcome!\
Forum: https://feedback.rsstranslator.com/ \
Telegram: https://t.me/rsstranslator

### About this repository
This repo is open source only for the RSS Translator front-end page code, and does not include the back-end code, which is only used for presentation and issue tracking!
