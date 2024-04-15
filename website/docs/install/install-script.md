## 最低安装要求

系统: Ubuntu 22.04 LTS(推荐) / Debian 12 / Fedora 37

内存: 建议512M以上(主程序100M，任务系统10M/worker)

Python: >= 3.10

## 下载安装脚本

`wget "https://raw.githubusercontent.com/rss-translator/RSS-Translator/main/deploy/install_update.sh"`

使用root赋予运行权限后执行

此脚本可多次运行，并可用于升级更新

```
sudo chmod +x install_update.sh
sudo ./install_update.sh
```

安装成功后，访问[http://127.0.0.1:8000](http://127.0.0.1:8000)

**默认账户：admin 密码：rsstranslator**

请登录后立即修改你的密码
