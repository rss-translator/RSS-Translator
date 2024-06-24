## 快速开始

首次登录后，建议点击右上方的修改密码修改默认密码

建议先添加翻译引擎后再添加Feed，除非只是想代理源

首次添加源后，需要一些时间进行翻译和生成，可能会耗时1分钟左右。

如果勾选了内容翻译，为了保持格式，会耗时较长时间。

状态说明：

<table> <tr> <td><img src="/assets/icon-loading.svg" width="20" height="20"></td> <td>正在处理中</td> </tr> <tr> <td><img src="/assets/icon-yes.svg" width="20" height="20"></td> <td>处理完成/有效</td> </tr> <tr> <td><img src="/assets/icon-no.svg" width="20" height="20"></td> <td>处理失败/无效</td> </tr> </table>

目前状态不会自动更新，请刷新页面以获取最新状态

## 添加翻译引擎
在左侧选择需要添加的翻译引擎提供商，点击 +增加 按钮
![add_translator_1](/assets/add_translator_1.png)
然后输入相关信息后，保存即可

注意检查是否是有效的，如果无效，则需要检查你输入的相关信息后重新保存验证
![translator_list](/assets/translator_list.png)

## 添加源
点击左侧原始源的 +增加 按钮
![core_feeds](/assets/core_feeds.png)
输入相关信息
保存后会跳转到源列表
![feed_list](/assets/feeds_list_2.png)
需要确保添加的源是有效的(Valid)，然后点击名称进入详情页
![feed_detail](/assets/feed_detail.png)
等待翻译源的状态(Status)完成后，即可复制旁边的FEED URL地址，并使用你喜欢的阅读器中订阅即可
![translated_feed_status](/assets/translated_feed_status.png)
如果只是翻译标题，并使用付费的翻译引擎，则需要翻译1分钟左右。

如果勾选了翻译内容，为了保持翻译后的格式，将会耗时较长时间。

## 动作
勾选需要操作的源，点击Action，选择对应选项，点击执行(Go)即可
![action](/assets/action.png)

## 合并订阅链接
使用以下链接可将所有翻译源合并为一个源：

`http://127.0.0.1:8000/rss/all/t`

也可以单独订阅某个类别的源：

`http://127.0.0.1:8000/rss/category/mycategory-1`

访问该网址后会实时进行合并，相对耗费资源，页面会缓存15分钟。

## 查看服务日志
登录后，在地址栏中访问log即可：http://127.0.0.1:8000/log

## 使用json格式的feed
只需在/rss后添加/json路径即可：

`http://127.0.0.1:8000/rss/json/<sid>`


## 字段说明
| 字段名 | Fields | 说明 |
| ------ | ---- | ---- |
| 原始的源 | Original Feeds | 原始的Feed源列表 |
| 翻译后的源 | Translated Feeds | 翻译后的Feed源列表 |
| 更新频率 | Update Frequency | 每次更新源的间隔(分钟) |
| 最大条目 | Max Posts | 最多翻译文章的数量，默认仅翻译前20篇 |
| 翻译引擎 | Translator engine | 使用的翻译引擎，只有有效的翻译引擎才会出现在下拉框中 |
| 名字 | Name | 可选，在管理页面显示的名称，默认为源标题 |
| 语言 | Language | 选择需要翻译的语言 |
| 翻译标题 | TRANSLATE TITLE | 翻译标题，默认勾选 |
| 翻译内容 | TRANSLATE CONTENT | 翻译内容，默认不勾选 |
| SID | SID | 自定义翻译源订阅地址，默认为随机生成的地址。仅支持首次添加时修改，添加后无法修改。比如sid设置为"hacker_news"，则订阅地址为"http://127.0.0.1:8000/rss/hacker_news"|
| 最后更新 | Last Updated(UTC) | 源最后更新的日期时间(UTC时区) |
| 最后拉去 | Last Pull(UTC) | 翻译器最后更新的日期时间(UTC时区) |
