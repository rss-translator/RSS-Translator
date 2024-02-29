#!/bin/bash
set -e
# please add yourself to rsstranslator group if you want to run rsstranslator as yourself
# usermod -a -G rsstranslator ${whoami}
repo_name="RSS-Translator"
repo_author="rss-translator"
repo_url="https://github.com/rss-translator/RSS-Translator"
#must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi
#python version >3.10
if [ "$(python3 -c 'import sys; print(sys.version_info >= (3, 10))')" != "True" ]; then
    echo " Python version need >3.10"
    exit 1
fi

script_dir="$(dirname "$(readlink -f "$0")")"
if [[ "$script_dir" == /home/rsstranslator* ]]; then
    echo "----- Get last install_update.sh from ${repo_url}/deploy/install_update.sh"
    wget "https://raw.githubusercontent.com/${repo_author}/${repo_name}/main/deploy/install_update.sh" -O /tmp/rsstranslator_install_update.sh
    chmod +x /tmp/rsstranslator_install_update.sh
    exec /tmp/rsstranslator_install_update.sh
    exit 0
fi

# Detect the package manager and install dependencies
if command -v yum >/dev/null  2>&1; then
    # For systems with yum like CentOS, Fedora, or RHEL
    yum update -y
    yum install python-virtualenv git zip -y
elif command -v apt-get >/dev/null  2>&1; then
    # For systems with apt like Debian or Ubuntu
    apt update && apt upgrade -y
    apt install python3-venv git zip -y
else
    echo "Unsupported package manager. Only yum and apt are supported."
    exit  1
fi

#backup data
if [ -d /home/rsstranslator/data  ] && [ "$(ls -A /home/rsstranslator/data)" ]; then
    echo "----- Backup current data to /tmp/rsstranslator_data"
    cp -rf /home/rsstranslator/data /tmp/rsstranslator_data
fi

echo "----- Create a nologin user: rsstranslator if not exist"
if ! id -u rsstranslator >/dev/null 2>&1; then
    useradd -r -s /sbin/nologin rsstranslator
fi

#check if repo_name-main.zip exist
if [ ! -f "${repo_name}-main.zip" ]; then
    echo "----- Download ${repo_name} from ${repo_url}"
    if [ -d ${repo_name} ]; then
        rm -rf ${repo_name}
    fi
    git clone ${repo_url}
    cp -rf ${repo_name} rsstranslator
    cp -rf rsstranslator /home/
else
    echo "----- Unzip ${repo_name}-main.zip"
    unzip -oq "${repo_name}-main.zip"
    cp -rf ${repo_name}-main rsstranslator
    cp -rf rsstranslator /home/
fi
rm -rf ${repo_name}
rm -rf ${repo_name}-main
rm -rf rsstranslator

if [ ! -d /home/rsstranslator/data ]; then
    echo "----- Create data folder"
    mkdir -p /home/rsstranslator/data
fi

echo "----- Correct folder permission "
if [ -d /home/rsstranslator ]; then
    chown -R rsstranslator:rsstranslator /home/rsstranslator
    chmod -R 775 /home/rsstranslator
    chmod a+x /home/rsstranslator/deploy/*.sh
else
    echo "/home/rsstranslator folder not exist, Please rerun this script"
    exit 1
fi

echo "----- Create a virtualenv: /home/rsstranslator/.venv if not exist"
if [ ! -d /home/rsstranslator/.venv ]; then
    sudo -u rsstranslator /bin/bash -c "python3 -m venv /home/rsstranslator/.venv"
fi

echo "----- Create rsstranslator.service to /etc/systemd/system/ if not exist"
if [ ! -f /etc/systemd/system/rsstranslator.service ]; then
    cp /home/rsstranslator/deploy/rsstranslator.service /etc/systemd/system/
fi

echo "----- Enable rsstranslator.service to start on boot"
systemctl daemon-reload
systemctl enable rsstranslator.service

show_progress() {
    local width=50
    local percent=$((100 * $1 / $2))
    local filled=$((width * $1 / $2))
    local empty=$((width - filled))
    local bar=$(printf "%${filled}s" '' | tr ' ' '#')
    local empty_bar=$(printf "%${empty}s" '' | tr ' ' '-')
    echo -ne "\rProgress: [${bar}${empty_bar}] ${percent}% \r"
}

echo "----- Initialize virtualenv"
total_packages=$(grep -v '^$' /home/rsstranslator/requirements/prod.txt | wc -l)
counter=0
while read package; do
    if [ ! -z "$package" ]; then
        sudo -u rsstranslator /home/rsstranslator/.venv/bin/pip install -q -U "$package" > /dev/null 2>&1
        let counter+=1
        show_progress $counter $total_packages
    fi
done < <(grep -v '^$' /home/rsstranslator/requirements/prod.txt)
echo -ne "\n"
if [ -d /tmp/rsstranslator_data ] && [ "$(ls -A /tmp/rsstranslator_data)" ]; then
    echo "----- Restore db"
    cp -rf /tmp/rsstranslator_data/* /home/rsstranslator/data/
    chown -R rsstranslator:rsstranslator /home/rsstranslator/data/
    chmod -R 775 /home/rsstranslator/data/
fi

echo "----- Migrate db"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py makemigrations"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py migrate"

echo "----- Create static files"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py collectstatic --noinput"

echo "----- Check default admin user"
sudo -u rsstranslator /bin/bash -c "/home/rsstranslator/.venv/bin/python /home/rsstranslator/manage.py create_default_superuser"

echo "----- Start rsstranslator.service"
systemctl restart rsstranslator.service

#echo "----- Check rsstranslator.service status"
#systemctl status rsstranslator.service
echo "----- Clean useless files"
rm -rf /tmp/rsstranslator_data
rm -rf rsstranslator_install_update.sh
rm -rf /home/rsstranslator/.git
rm -rf /home/rsstranslator/data/app.log

echo "------------------------------"
echo "| If you want to change address or port, please edit /home/rsstranslator/deploy/start.sh"
echo "| And then run 'systemctl restart rsstranslator'"
echo "------------------------------"
echo "| If you want enable https, Please install caddy first: https://caddyserver.com/docs/install#debian-ubuntu-raspbian"
echo "| Then edit /home/rsstranslator/deploy/Caddyfile to change domain name"
echo "| And cp /home/rsstranslator/deploy/Caddyfile to /etc/caddy/Caddyfile"
echo "| Finally run 'systemctl restart caddy'"
echo "------------------------------"
echo "| INFO: Default admin user: admin, Password: rsstranslator"
echo "| Please change admin password after login"
echo "------------------------------"
echo "| You can check service status by run 'systemctl status rsstranslator'"
echo "| And check log by run 'journalctl -u rsstranslator' or check /home/rsstranslator/data/app.log"
echo "| INFO: Success install RSS Translator, service run on 0.0.0.0:8000 (http)"
echo "------------------------------"

