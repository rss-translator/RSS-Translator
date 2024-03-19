[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/KnVkVX?referralCode=QWy2ii)

## 注意事项

1. 如果绑定了域名，请修改Railway的变量`CSRF_TRUSTED_ORIGINS`的值为你的域名。
2. 默认账户：admin 默认密码：rsstranslator
3. 请登录后立即修改你的密码
4. 请不要修改变量PORT的值，否则可能导致无法访问

## 可选变量

`HUEY_WORKERS` 调整线程数量，如果运行卡顿，可修改到1，默认为10

`default_update_frequency` 调整默认的更新时间（分钟），默认为30

`default_max_posts` 调整每个源的默认最大翻译数量，默认为20
