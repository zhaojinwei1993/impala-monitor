#!/bin/bash

# Impala Node Collector 部署脚本

set -e

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_NAME="impala_node_collector"
SERVICE_NAME="impala-node-collector"
INSTALL_DIR="/opt/impala-monitor"
CONFIG_DIR="/etc/impala-monitor"
LOG_DIR="/var/log/impala-monitor"
USER="impala-monitor"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# 创建用户
create_user() {
    if ! id "$USER" &>/dev/null; then
        log_info "Creating user $USER"
        useradd -r -s /bin/false -d /nonexistent "$USER"
    else
        log_info "User $USER already exists"
    fi
}

# 创建目录
create_directories() {
    log_info "Creating directories"
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    
    chown -R "$USER:$USER" "$INSTALL_DIR"
    chown -R "$USER:$USER" "$CONFIG_DIR"
    chown -R "$USER:$USER" "$LOG_DIR"
}

# 安装 Python 依赖
install_dependencies() {
    log_info "Installing Python dependencies"
    
    # 检查 Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # 安装 pip 依赖
    pip3 install prometheus_client requests pyyaml
}

# 复制文件
copy_files() {
    log_info "Copying files"
    
    # 复制主程序
    cp "$SCRIPT_DIR/${COLLECTOR_NAME}.py" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/${COLLECTOR_NAME}.py"
    
    # 复制配置文件
    if [[ ! -f "$CONFIG_DIR/node_config.yaml" ]]; then
        cp "$SCRIPT_DIR/node_config.yaml" "$CONFIG_DIR/"
    else
        log_warn "Configuration file already exists, skipping"
    fi
    
    chown -R "$USER:$USER" "$INSTALL_DIR"
    chown -R "$USER:$USER" "$CONFIG_DIR"
}

# 创建 systemd 服务
create_service() {
    log_info "Creating systemd service"
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Impala Node Metrics Collector
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/${COLLECTOR_NAME}.py --config $CONFIG_DIR/node_config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
}

# 启动服务
start_service() {
    log_info "Starting service"
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    # 检查服务状态
    sleep 3
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Service started successfully"
        systemctl status "$SERVICE_NAME" --no-pager -l
    else
        log_error "Service failed to start"
        systemctl status "$SERVICE_NAME" --no-pager -l
        exit 1
    fi
}

# 显示使用信息
show_usage() {
    log_info "Deployment completed successfully!"
    echo
    echo "Service management commands:"
    echo "  Start:   systemctl start $SERVICE_NAME"
    echo "  Stop:    systemctl stop $SERVICE_NAME"
    echo "  Restart: systemctl restart $SERVICE_NAME"
    echo "  Status:  systemctl status $SERVICE_NAME"
    echo "  Logs:    journalctl -u $SERVICE_NAME -f"
    echo
    echo "Configuration file: $CONFIG_DIR/node_config.yaml"
    echo "Log directory: $LOG_DIR"
    echo
    echo "Metrics will be available at: http://localhost:9356/metrics"
}

# 主函数
main() {
    log_info "Starting Impala Node Collector deployment"
    
    check_root
    create_user
    create_directories
    install_dependencies
    copy_files
    create_service
    start_service
    show_usage
}

# 处理命令行参数
case "${1:-install}" in
    install)
        main
        ;;
    uninstall)
        log_info "Uninstalling Impala Node Collector"
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        systemctl daemon-reload
        rm -rf "$INSTALL_DIR"
        log_warn "Configuration and logs preserved in $CONFIG_DIR and $LOG_DIR"
        log_info "Uninstallation completed"
        ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        exit 1
        ;;
esac
