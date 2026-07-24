#!/bin/sh
# Script author @VanillaNahida
# This file is used to automatically download the required files for this project with one click and automatically create the directories.
# Currently only supports X86 version of Ubuntu system, other systems have not been tested.

# Define interrupt handling function
handle_interrupt() {
    echo ""
    echo "Installation interrupted by user (Ctrl+C or Esc)"
    echo "If you need to reinstall, please run the script again"
    exit 1
}

# Set signal trap to handle Ctrl+C
trap handle_interrupt SIGINT

# Handle Esc key
# Save terminal settings
old_stty_settings=$(stty -g)
# Set terminal to respond immediately, no echo
stty -icanon -echo min 1 time 0

# Background process to detect Esc key
(while true; do
    read -r key
    if [[ $key == $'\e' ]]; then
        # Esc key detected, trigger interrupt handling
        kill -SIGINT $$
        break
    fi
done) &

# Restore terminal settings when script ends
trap 'stty "$old_stty_settings"' EXIT


# Print colored ASCII art
echo -e "\e[1;32m"  # Set color to light green
cat << "EOF"
Script author: @Bilibili Vanilla-flavored Nahida Meow
 __      __            _  _  _            _   _         _      _      _        
 \ \    / /           (_)| || |          | \ | |       | |    (_)    | |       
  \ \  / /__ _  _ __   _ | || |  __ _    |  \| |  __ _ | |__   _   __| |  __ _ 
   \ \/ // _` || '_ \ | || || | / _` |   | . ` | / _` || '_ \ | | / _` | / _` |
    \  /| (_| || | | || || || || (_| |   | |\  || (_| || | | || || (_| || (_| |
     \/  \__,_||_| |_||_||_||_| \__,_|   |_| \_| \__,_||_| |_||_| \__,_| \__,_|                                                                                                                                                                                                                               
EOF
echo -e "\e[0m"  # Reset color
echo -e "\e[1;36m  Xiaozhi Server Full Deployment One-Click Installation Script Ver 0.2 Updated on August 20, 2025 \e[0m\n"
sleep 1



# Check and install whiptail
check_whiptail() {
    if ! command -v whiptail &> /dev/null; then
        echo "Installing whiptail..."
        apt update
        apt install -y whiptail
    fi
}

check_whiptail

# Create confirmation dialog
whiptail --title "Installation Confirmation" --yesno "About to install Xiaozhi Server, do you want to continue?" \
  --yes-button "Continue" --no-button "Exit" 10 50

# Execute operation based on user selection
case $? in
  0)
    ;;
  1)
    exit 1
    ;;
esac

# Check root privileges
if [ $EUID -ne 0 ]; then
    whiptail --title "Permission Error" --msgbox "Please run this script with root privileges" 10 50
    exit 1
fi

# Check system version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "debian" ] && [ "$ID" != "ubuntu" ]; then
        whiptail --title "System Error" --msgbox "This script only supports execution on Debian/Ubuntu systems" 10 60
        exit 1
    fi
else
    whiptail --title "System Error" --msgbox "Cannot determine system version, this script only supports execution on Debian/Ubuntu systems" 10 60
    exit 1
fi

# Download configuration file function
check_and_download() {
    local filepath=$1
    local url=$2
    if [ ! -f "$filepath" ]; then
        if ! curl -fL --progress-bar "$url" -o "$filepath"; then
            whiptail --title "Error" --msgbox "Failed to download file ${filepath}" 10 50
            exit 1
        fi
    else
        echo "File ${filepath} already exists, skipping download"
    fi
}

# Check if already installed
check_installed() {
    # Check if directory exists and is not empty
    if [ -d "/opt/xiaozhi-server/" ] && [ "$(ls -A /opt/xiaozhi-server/)" ]; then
        DIR_CHECK=1
    else
        DIR_CHECK=0
    fi
    
    # Check if container exists
    if docker inspect project-alice-server > /dev/null 2>&1; then
        CONTAINER_CHECK=1
    else
        CONTAINER_CHECK=0
    fi
    
    # Both checks passed
    if [ $DIR_CHECK -eq 1 ] && [ $CONTAINER_CHECK -eq 1 ]; then
        return 0  # Installed
    else
        return 1  # Not installed
    fi
}

# Update related
if check_installed; then
    if whiptail --title "Installation Detected" --yesno "Xiaozhi server is already installed, do you want to upgrade?" 10 60; then
        # User selected upgrade, perform cleanup operations
        echo "Starting upgrade operations..."
        
        # Stop and remove all docker-compose services
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml down
        
        # Stop and delete specific containers (considering containers might not exist)
        containers=(
            "project-alice-server"
            "project-alice-server-web"
            "project-alice-server-db"
            "project-alice-server-redis"
        )
        
        for container in "${containers[@]}"; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                docker stop "$container" >/dev/null 2>&1 && \
                docker rm "$container" >/dev/null 2>&1 && \
                echo "Successfully removed container: $container"
            else
                echo "Container does not exist, skipping: $container"
            fi
        done
        
        # Delete specific images (considering images might not exist)
        images=(
            "ghcr.nju.edu.cn/xinnan-tech/project-alice-server:server_latest"
            "ghcr.nju.edu.cn/xinnan-tech/project-alice-server:web_latest"
        )
        
        for image in "${images[@]}"; do
            if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${image}$"; then
                docker rmi "$image" >/dev/null 2>&1 && \
                echo "Successfully deleted image: $image"
            else
                echo "Image does not exist, skipping: $image"
            fi
        done
        
        echo "All cleanup operations completed"
        
        # Backup original configuration files
        mkdir -p /opt/xiaozhi-server/backup/
        if [ -f /opt/xiaozhi-server/data/.config.yaml ]; then
            cp /opt/xiaozhi-server/data/.config.yaml /opt/xiaozhi-server/backup/.config.yaml
            echo "Original configuration file backed up to /opt/xiaozhi-server/backup/.config.yaml"
        fi
        
        # Download the latest configuration files
        check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/project-alice-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
        check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/project-alice-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
        
        # Start Docker service
        echo "Starting the latest version of the service..."
        # Mark upgrade as completed, skip subsequent download steps
        UPGRADE_COMPLETED=1
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    else
          whiptail --title "Skip Upgrade" --msgbox "Upgrade cancelled, will continue using the current version." 10 50
          # Skip upgrade, continue with subsequent installation process
    fi
fi


# Check curl installation
if ! command -v curl &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "curl not detected, installing..."
    apt update
    apt install -y curl
else
    echo "------------------------------------------------------------"
    echo "curl is already installed, skipping installation step"
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "Docker not detected, installing..."
    
    # Use domestic mirror source instead of official source
    DISTRO=$(lsb_release -cs)
    MIRROR_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
    GPG_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg"
    
    # Install basic dependencies
    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    
    # Create key directory and add domestic mirror source key
    mkdir -p /etc/apt/keyrings
    curl -fsSL "$GPG_URL" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add domestic mirror source
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $MIRROR_URL $DISTRO stable" \
        > /etc/apt/sources.list.d/docker.list
    
    # Add alternate official source key (to avoid domestic source key verification failure)
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7EA0A9C3F273FCD8 2>/dev/null || \
    echo "Warning: Failed to add some keys, continuing installation attempt..."
    
    # Install Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    
    # Start service
    systemctl start docker
    systemctl enable docker
    
    # Check if installation is successful
    if docker --version; then
        echo "------------------------------------------------------------"
        echo "Docker installation completed!"
    else
        whiptail --title "Error" --msgbox "Docker installation failed, please check the logs." 10 50
        exit 1
    fi
else
    echo "Docker is already installed, skipping installation step"
fi

# Docker mirror source configuration
MIRROR_OPTIONS=(
    "1" "Xuanyuan Mirror (Recommended)"
    "2" "Tencent Cloud Mirror"
    "3" "USTC Mirror"
    "4" "NetEase 163 Mirror"
    "5" "Huawei Cloud Mirror"
    "6" "Alibaba Cloud Mirror"
    "7" "Custom Mirror"
    "8" "Skip Configuration"
)

MIRROR_CHOICE=$(whiptail --title "Select Docker Mirror Source" --menu "Please select the Docker mirror source to use" 20 60 10 \
"${MIRROR_OPTIONS[@]}" 3>&1 1>&2 2>&3) || {
    echo "User cancelled selection, exiting script"
    exit 1
}

case $MIRROR_CHOICE in
    1) MIRROR_URL="https://docker.xuanyuan.me" ;; 
    2) MIRROR_URL="https://mirror.ccs.tencentyun.com" ;; 
    3) MIRROR_URL="https://docker.mirrors.ustc.edu.cn" ;; 
    4) MIRROR_URL="https://hub-mirror.c.163.com" ;; 
    5) MIRROR_URL="https://05f073ad3c0010ea0f4bc00b7105ec20.mirror.swr.myhuaweicloud.com" ;; 
    6) MIRROR_URL="https://registry.aliyuncs.com" ;; 
    7) MIRROR_URL=$(whiptail --title "Custom Mirror Source" --inputbox "Please enter the full mirror source URL:" 10 60 3>&1 1>&2 2>&3) ;; 
    8) MIRROR_URL="" ;; 
esac

if [ -n "$MIRROR_URL" ]; then
    mkdir -p /etc/docker
    if [ -f /etc/docker/daemon.json ]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
    fi
    cat > /etc/docker/daemon.json <<EOF
{
    "dns": ["8.8.8.8", "114.114.114.114"],
    "registry-mirrors": ["$MIRROR_URL"]
}
EOF
    whiptail --title "Configuration Successful" --msgbox "Successfully added mirror source: $MIRROR_URL\nPlease press Enter to restart Docker service and continue..." 12 60
    echo "------------------------------------------------------------"
    echo "Starting to restart Docker service..."
    systemctl restart docker.service
fi

# Create installation directory
echo "------------------------------------------------------------"
echo "Starting to create installation directory..."
# Check and create data directory
if [ ! -d /opt/xiaozhi-server/data ]; then
    mkdir -p /opt/xiaozhi-server/data
    echo "Data directory created: /opt/xiaozhi-server/data"
else
    echo "Directory xiaozhi-server/data already exists, skipping creation"
fi

# Check and create models directory
if [ ! -d /opt/xiaozhi-server/models/SenseVoiceSmall ]; then
    mkdir -p /opt/xiaozhi-server/models/SenseVoiceSmall
    echo "Models directory created: /opt/xiaozhi-server/models/SenseVoiceSmall"
else
    echo "Directory xiaozhi-server/models/SenseVoiceSmall already exists, skipping creation"
fi

echo "------------------------------------------------------------"
echo "Starting to download speech recognition model"
# Download model file
MODEL_PATH="/opt/xiaozhi-server/models/SenseVoiceSmall/model.pt"
if [ ! -f "$MODEL_PATH" ]; then
    (
    for i in {1..20}; do
        echo $((i*5))
        sleep 0.5
    done
    ) | whiptail --title "Downloading" --gauge "Starting to download speech recognition model..." 10 60 0
    curl -fL --progress-bar https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt -o "$MODEL_PATH" || {
        whiptail --title "Error" --msgbox "Failed to download model.pt file" 10 50
        exit 1
    }
else
    echo "model.pt file already exists, skipping download"
fi

# Execute download only if it is not an upgrade completion
if [ -z "$UPGRADE_COMPLETED" ]; then
    check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/project-alice-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
    check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/project-alice-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
fi

# Start Docker service
(
echo "------------------------------------------------------------"
echo "Pulling Docker images..."
echo "This may take a few minutes, please be patient"
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d

if [ $? -ne 0 ]; then
    whiptail --title "Error" --msgbox "Docker service failed to start, please try changing the mirror source and run this script again" 10 60
    exit 1
fi

echo "------------------------------------------------------------"
echo "Checking service startup status..."
TIMEOUT=300
START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - START_TIME)) -gt $TIMEOUT ]; then
        whiptail --title "Error" --msgbox "Service startup timeout, expected log content not found within specified time" 10 60
        exit 1
    fi
    
    if docker logs project-alice-server-web 2>&1 | grep -q "Started AdminApplication in"; then
        break
    fi
    sleep 1
done

    echo "Server started successfully! Completing configuration..."
    echo "Starting services..."
    docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    echo "Service startup complete!"
)

# Secret key configuration

# Get server public IP address
PUBLIC_IP=$(hostname -I | awk '{print $1}')
whiptail --title "Configure Server Secret Key" --msgbox "Please use a browser to visit the link below, open the control console and register an account: \n\nIntranet address: http://127.0.0.1:8002/\nPublic address: http://$PUBLIC_IP:8002/ (If it is a cloud server, please allow ports 8000, 8001, 8002 in the server security group).\n\nThe first registered user will be the super administrator, and users registered afterwards will be regular users. Regular users can only bind devices and configure agents; super administrators can manage models, users, parameter configurations, etc.\n\nAfter registration, please press Enter to continue" 18 70
SECRET_KEY=$(whiptail --title "Configure Server Secret Key" --inputbox "Please log in to the control console with the super administrator account\nIntranet address: http://127.0.0.1:8002/\nPublic address: http://$PUBLIC_IP:8002/\nIn the top menu Parameter Dictionary -> Parameter Management, find the parameter code: server.secret (Server Secret Key) \nCopy this parameter value and enter it into the input box below\n\nPlease enter the secret key (leave blank to skip configuration):" 15 60 3>&1 1>&2 2>&3)

if [ -n "$SECRET_KEY" ]; then
    python3 -c "
import sys, yaml; 
config_path = '/opt/xiaozhi-server/data/.config.yaml'; 
with open(config_path, 'r') as f: 
    config = yaml.safe_load(f) or {}; 
config['manager-api'] = {'url': 'http://project-alice-server-web:8002/xiaozhi', 'secret': '$SECRET_KEY'}; 
with open(config_path, 'w') as f: 
    yaml.dump(config, f); 
"
    docker restart project-alice-server
fi

# Get and display address information
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Fix the issue where ws cannot be obtained from the log file, change to hardcoding
whiptail --title "Installation Complete!" --msgbox "\
Server-related addresses are as follows:\n\
Management backend access address: http://$LOCAL_IP:8002\n\
OTA Address: http://$LOCAL_IP:8002/xiaozhi/ota/\n\
Vision analysis API address: http://$LOCAL_IP:8003/mcp/vision/explain\n\
WebSocket Address: ws://$LOCAL_IP:8000/xiaozhi/v1/\n\
\nInstallation complete! Thank you for using!\nPress Enter to exit..." 16 70