#!/bin/bash
# Impala Query Killer 部署脚本

set -e

INSTALL_DIR="/opt/impala-monitor"
SERVICE_NAME="impala-query-killer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 配置参数
IMPALA_HOST="${IMPALA_HOST:-}"
IMPALA_PORT="${IMPALA_PORT:-25000}"
FEISHU_WEBHOOK="${FEISHU_WEBHOOK:-}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
MAX_DURATION="${MAX_DURATION:-600}"
MAX_MEMORY_GB="${MAX_MEMORY_GB:-1024}"

usage() {
    echo "Usage: $0 {install|uninstall|restart|status}"
    echo ""
    echo "Environment variables:"
    echo "  IMPALA_HOST      - Impala host IP (required)"
    echo "  IMPALA_PORT      - Impala port (default: 25000)"
    echo "  FEISHU_WEBHOOK   - Feishu webhook URL (required)"
    echo "  CHECK_INTERVAL   - Check interval in seconds (default: 60)"
    echo "  MAX_DURATION     - Max query duration in seconds (default: 600)"
    echo "  MAX_MEMORY_GB    - Max query memory in GB (default: 1024)"
    exit 1
}

install() {
    echo "Installing Impala Query Killer..."
    
    # 检查必需参数
    if [ -z "$IMPALA_HOST" ]; then
        echo "Error: IMPALA_HOST is required"
        exit 1
    fi
    
    if [ -z "$FEISHU_WEBHOOK" ]; then
        echo "Error: FEISHU_WEBHOOK is required"
        exit 1
    fi
    
    # 创建安装目录
    sudo mkdir -p "$INSTALL_DIR/src"
    sudo mkdir -p "$INSTALL_DIR/logs"
    
    # 复制文件
    sudo cp "$PROJECT_ROOT/monitor/src/query_killer.py" "$INSTALL_DIR/src/"
    sudo cp "$PROJECT_ROOT/monitor/src/impala_exporter.py" "$INSTALL_DIR/src/"
    sudo cp "$PROJECT_ROOT/monitor/requirements.txt" "$INSTALL_DIR/"
    
    # 安装依赖
    sudo pip3 install -r "$INSTALL_DIR/requirements.txt"
    
    # 创建 systemd 服务文件
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Impala Query Killer
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/src
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/query_killer.py \\
    --host $IMPALA_HOST \\
    --port $IMPALA_PORT \\
    --feishu-webhook "$FEISHU_WEBHOOK" \\
    --check-interval $CHECK_INTERVAL \\
    --max-duration $MAX_DURATION \\
    --max-memory-gb $MAX_MEMORY_GB
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/query_killer.log
StandardError=append:$INSTALL_DIR/logs/query_killer.log

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载 systemd
    sudo systemctl daemon-reload
    
    # 启动服务
    sudo systemctl enable ${SERVICE_NAME}
    sudo systemctl start ${SERVICE_NAME}
    
    echo "Installation completed!"
    echo "Service status:"
    sudo systemctl status ${SERVICE_NAME} --no-pager
}

uninstall() {
    echo "Uninstalling Impala Query Killer..."
    
    # 停止服务
    sudo systemctl stop ${SERVICE_NAME} || true
    sudo systemctl disable ${SERVICE_NAME} || true
    
    # 删除服务文件
    sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
    
    # 删除安装目录（保留日志）
    sudo rm -rf "$INSTALL_DIR/src"
    
    # 重新加载 systemd
    sudo systemctl daemon-reload
    
    echo "Uninstallation completed!"
}

restart() {
    echo "Restarting Impala Query Killer..."
    sudo systemctl restart ${SERVICE_NAME}
    sudo systemctl status ${SERVICE_NAME} --no-pager
}

status() {
    sudo systemctl status ${SERVICE_NAME} --no-pager
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
