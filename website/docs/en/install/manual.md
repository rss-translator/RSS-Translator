不推荐使用手动安装

## 最低安装要求

系统: Ubuntu 22.04 LTS(推荐) / Debian 12 / Fedora 37

内存: 建议512M以上

Python: >= 3.10

## 安装必要软件

`sudo apt install python3-venv git zip -y`

## 下载项目

`git clone https://github.com/rss-translator/RSS-Translator.git`

## 创建执行用户

```
sudo useradd -r -s /sbin/nologin rsstranslator
sudo usermod -a -G rsstranslator your_user_name
```

## 移动文件夹并修正权限

```
mv -f RSS-Translator /home/rsstranslator
mkdir /home/rsstranslator/data
sudo chown -R rsstranslator:rsstranslator /home/rsstranslator
sudo chmod -R 775 /home/rsstranslator
sudo chmod a+x /home/rsstranslator/deploy/*.sh
```

## 创建虚拟环境

```
sudo -u rsstranslator /bin/bash -c "python3 -m venv /home/rsstranslator/.venv"
```

## 安装依赖

`sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/pip install -q -r /home/rsstranslator/requirements/prod.txt"`

## 创建服务

`sudo nano /etc/systemd/system/rsstranslator.service`

粘贴并修改下面的内容

```
[Unit]
Description=RSS Translator Application Service
After=network.target

[Service]
Type=simple
User=rsstranslator
Group=rsstranslator
WorkingDirectory=/home/rsstranslator/
ExecStart=/home/rsstranslator/deploy/start.sh
Restart=always
RestartSec=2
Environment="DEBUG=0"
Environment="LOG_LEVEL=ERROR"
Environment="HUEY_WORKERS=10"
Environment="default_update_frequency=30"
Environment="default_max_posts=20"

[Install]
WantedBy=multi-user.target
```

## 重启daemon并开机自启动

```
sudo systemctl daemon-reload
sudo systemctl enable rsstranslator.service
```

## 初始化运行环境

```
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py makemigrations"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py migrate"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py collectstatic --noinput"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py create_default_superuser"
```

## 启动服务

`systemctl start rsstranslator.service`

## 查看服务状态

`systemctl status rsstranslator.service`

安装完成，访问 http://127.0.0.1:8000

**默认账户：admin 密码：rsstranslator**

请登录后立即修改你的密码

## 升级
`sudo ./home/rsstranslator/deploy/install_update.sh`

## 卸载
`sudo ./home/rsstranslator/deploy/uninstall.sh`

注意：该卸载脚本并不会删除/tmp目录下的数据备份文件，以防万一
