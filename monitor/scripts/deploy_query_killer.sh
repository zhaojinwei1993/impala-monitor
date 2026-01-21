#!/bin/bash
# Impala Query Killer 部署脚本

set -e

INSTALL_DIR="/opt/impala-monitor"
SERVICE_NAME="impala-query-killer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
    echo "Usage: $0 {install|uninstall|restart|status}"
    echo ""
    echo "Before install, you must:"
    echo "  1. sudo mkdir -p /opt/impala-monitor/config"
    echo "  2. sudo cp monitor/config/query_killer.conf /opt/impala-monitor/config/"
    echo "  3. sudo vim /opt/impala-monitor/config/query_killer.conf  # Edit configuration"
    echo "  4. sudo $0 install"
    exit 1
}

install() {
    echo "Installing Impala Query Killer..."
    
    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run as root"
        echo "Please use: sudo $0 install"
        exit 1
    fi
    
    # 检查配置文件是否存在
    if [ ! -f "$INSTALL_DIR/config/query_killer.conf" ]; then
        echo "Error: Configuration file not found: $INSTALL_DIR/config/query_killer.conf"
        echo ""
        echo "Please follow these steps:"
        echo "  1. sudo mkdir -p $INSTALL_DIR/config"
        echo "  2. sudo cp $PROJECT_ROOT/monitor/config/query_killer.conf $INSTALL_DIR/config/"
        echo "  3. sudo vim $INSTALL_DIR/config/query_killer.conf  # Edit the configuration"
        echo "  4. sudo $0 install"
        exit 1
    fi
    
    # 创建安装目录
    mkdir -p "$INSTALL_DIR/src"
    mkdir -p "$INSTALL_DIR/logs"
    
    # 复制文件
    cp "$PROJECT_ROOT/monitor/src/query_killer.py" "$INSTALL_DIR/src/"
    cp "$PROJECT_ROOT/monitor/src/impala_exporter.py" "$INSTALL_DIR/src/"
    cp "$PROJECT_ROOT/monitor/requirements.txt" "$INSTALL_DIR/"
    
    # 安装依赖
    pip3 install -r "$INSTALL_DIR/requirements.txt"
    
    echo "Using configuration file: $INSTALL_DIR/config/query_killer.conf"
    
    # 创建 systemd 服务文件
    tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Impala Query Killer
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/src
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/query_killer.py --config $INSTALL_DIR/config/query_killer.conf
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/query_killer.log
StandardError=append:$INSTALL_DIR/logs/query_killer.log

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启动服务
    systemctl enable ${SERVICE_NAME}
    systemctl start ${SERVICE_NAME}
    
    echo "Installation completed!"
    echo "Service status:"
    systemctl status ${SERVICE_NAME} --no-pager
}

uninstall() {
    echo "Uninstalling Impala Query Killer..."
    
    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run as root"
        echo "Please use: sudo $0 uninstall"
        exit 1
    fi
    
    # 停止服务
    systemctl stop ${SERVICE_NAME} || true
    systemctl disable ${SERVICE_NAME} || true
    
    # 删除服务文件
    rm -f /etc/systemd/system/${SERVICE_NAME}.service
    
    # 删除安装目录（保留日志）
    rm -rf "$INSTALL_DIR/src/query_killer.py"
    rm -rf "$INSTALL_DIR/config/query_killer.conf"
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    echo "Uninstallation completed!"
}

restart() {
    echo "Restarting Impala Query Killer..."
    
    # 检查是否为 root 用户
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run as root"
        echo "Please use: sudo $0 restart"
        exit 1
    fi
    
    systemctl restart ${SERVICE_NAME}
    systemctl status ${SERVICE_NAME} --no-pager
}

status() {
    systemctl status ${SERVICE_NAME} --no-pager
}

case "$1" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        usage
        ;;
esac
