## Minimum Installation Requirements

System: Ubuntu 22.04 LTS (recommended) / Debian 12 / Fedora 37

RAM: 512M or more recommended (100M for main application, 10M/worker for task system)

Python: >= 3.10

## Download the installation script

`wget "https://raw.githubusercontent.com/rss-translator/RSS-Translator/main/deploy/install_update.sh"`

Execute it after giving run privileges with root

This script can be run multiple times and can be used for upgrading updates

``
sudo chmod +x install_update.sh
sudo . /install_update.sh
```

After successful installation, visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

**default account: admin, password: rsstranslator**

Please change your password immediately after logging in
