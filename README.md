# [RSS翻译器](https://www.rsstranslator.com/)
[EN](README_EN.md) / [中文](README.md) 

RSS 翻译器历时 3 个月，总算开始内测了。\
网站: https://www.rsstranslator.com \
开发的主要原因是解决个人需求，关注了很多国外的博主，但英文标题不利于快速筛选，因此做了 RSS翻译器。

### 技术栈：
前端: 无框架，纯手工打造(HTML+JS+CSS)\
后端: Python\
前端部署在 Cloudflare 的 Pages\
后端和数据库部署在 Appwrite\
翻译引擎: GPT-3.5 / 被过滤的内容将用 DeepL 翻译

### 使用方法:
打开[RSS翻译器](https://www.rsstranslator.com/)，输入 feed 源地址，选择目标语言，点击 Create 即可

### 注意事项:
1.仅翻译标题\
2.免费，如果对您有帮助，欢迎[赞助](https://github.com/sponsors/versun)以维持免费状态\
3.较大的 feed 源会花费较长的时间进行翻译(5 分钟左右)（仅翻译前 1000 个标题）\
4.所有 feed 每 20 分钟自动更新一次\
5.在网页端重新输入同一个 feed 源将会强制更新一次

目前还是内测阶段，欢迎提 Bug\
论坛：https://feedback.rsstranslator.com/ \
Telegram: https://t.me/rsstranslator

### 关于这个仓库
这个仓库仅用于展示和Issue跟踪，只有前端页面代码是开源的，并不包含后端代码。\
后期将会全部开源，并支持自部署