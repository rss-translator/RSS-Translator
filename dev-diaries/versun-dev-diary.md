# 2024-07-22
加了OpenL翻译引擎，这个确实不错，集成了很多第三方翻译服务，价格也还可以
还加了Kagi的fastgpt和summarize，fastgpt翻译的话没法关掉网络搜索，总是会有角标，不是很建议用来翻译，不过summarize测试下来还不错，价格的话有点贵，用不起

还有一个bug待修复：google gemini的内容审核参数得加下，实在很不喜欢google的文档，ai有好几个平台，api还不一样，好烦

# 2024-07-04
想使用[django-tasks](https://github.com/RealOrangeOne/django-tasks)来代替huey做为任务管理，但因为还在开发中，所以担心稳定性。主要是因为它的issues中有几个我在使用huey时遇到的问题，且正在解决，但huey还遥遥无期。。。。

添加了huey的shutdown动作，flush所有任务（包括revoke的任务，防止无用的任务堆积）

huey在revoke一个task后，并不会删除这个task，如果之后继续revoke的话，还会重复revoke一遍，本来想搭配restore_by_id来恢复并重新预约任务，但需要存储task的result才能调用reschedule，所以暂时放弃了。

先这样吧，又不是不能用，等django-tasks完善吧

# 2024-07-03
看来还是有必要添加个开发日记，因为有些代码现在看起来很傻逼，但就是不知道当初为啥会这么写，感觉是为了某种边缘情况，但就是记不起来。

开发日记的灵感来源于：https://github.com/cozemble/breezbook/discussions/32

---
今天主要是重构了core/admin.py，原先的代码太乱了。
整个文件直接丢给pplx的claude 3.5 sonnet，效果非常好，基本一次就成了

然后顺便发现了revoke_tasks_by_arg函数的使用逻辑有点问题:
t_feed_force_update不应该调用revoke_tasks_by_arg，因为它是通过update_original_feed task来调用的，只有original_feed才会预约，而update_translated_feed task是实时性的，所以应该在update_translated_feed里检查任务唯一性就行了。

o_feed_force_update也不用revoke_tasks_by_arg，直接放在update_original_feed task更方便直观，否则task完全不知道可能会在哪里被revoke掉

新发布的版本，还是先发布pre release，push到docker dev标签，自己先测试一段时间再push到latest
