#!/bin/bash
"""
Impala Node Collector 部署脚本
使用root用户部署
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_DIR="/opt/impala-monitor"
SERVICE_NAME="impala-monitor"

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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing dependencies..."
    
    # 检测操作系统
    if command -v yum &> /dev/null; then
        # CentOS/RHEL
        yum update -y
        yum install -y python3 python3-pip
    elif command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        apt-get update
        apt-get install -y python3 python3-pip
    else
        log_error "Unsupported operating system"
        exit 1
    fi
    
    # 安装 Python 依赖
    pip3 install -r "$PROJECT_ROOT/monitor/requirements.txt"
}

install_files() {
    log_info "Installing files to $INSTALL_DIR..."
    
    # 创建安装目录
    mkdir -p "$INSTALL_DIR"/{src,config,logs}
    
    # 复制源代码
    cp "$PROJECT_ROOT/monitor/src/impala_exporter.py" "$INSTALL_DIR/src/"
    cp "$PROJECT_ROOT/monitor/src/impala_monitor.py" "$INSTALL_DIR/src/"
    
    # 复制配置文件
    cp "$PROJECT_ROOT/monitor/config/node_config.yaml" "$INSTALL_DIR/config/"
    
    # 设置权限
    chmod +x "$INSTALL_DIR/src/impala_monitor.py"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Impala Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR/src
ExecStart=/usr/bin/python3 $INSTALL_DIR/src/impala_monitor.py --config $INSTALL_DIR/config/node_config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# 环境变量
Environment=PYTHONPATH=$INSTALL_DIR/src

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "Systemd service created"
}

configure_firewall() {
    log_info "Configuring firewall..."
    
    # 获取配置的端口
    METRICS_PORT=$(grep "metrics_port:" "$INSTALL_DIR/config/node_config.yaml" | awk '{print $2}')
    METRICS_PORT=${METRICS_PORT:-9356}
    
    if command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL with firewalld
        firewall-cmd --permanent --add-port="$METRICS_PORT/tcp"
        firewall-cmd --reload
        log_info "Firewall configured for port $METRICS_PORT"
    elif command -v ufw &> /dev/null; then
        # Ubuntu with ufw
        ufw allow "$METRICS_PORT/tcp"
        log_info "UFW configured for port $METRICS_PORT"
    else
        log_warn "No firewall management tool found, please manually open port $METRICS_PORT"
    fi
}

start_service() {
    log_info "Starting $SERVICE_NAME service..."
    
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    # 等待服务启动
    sleep 5
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Service started successfully"
        
        # 显示状态
        systemctl status "$SERVICE_NAME" --no-pager -l
        
        # 测试指标端点
        METRICS_PORT=$(grep "metrics_port:" "$INSTALL_DIR/config/node_config.yaml" | awk '{print $2}')
        METRICS_PORT=${METRICS_PORT:-9356}
        
        log_info "Testing metrics endpoint..."
        if curl -s "http://localhost:$METRICS_PORT/metrics" > /dev/null; then
            log_info "✓ Metrics endpoint is accessible at http://localhost:$METRICS_PORT/metrics"
        else
            log_warn "✗ Metrics endpoint test failed"
        fi
    else
        log_error "Failed to start service"
        systemctl status "$SERVICE_NAME" --no-pager -l
        exit 1
    fi
}

stop_service() {
    log_info "Stopping $SERVICE_NAME service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME"
        log_info "Service stopped"
    else
        log_info "Service is not running"
    fi
}

uninstall() {
    log_info "Uninstalling Impala Monitor..."
    
    # 停止服务
    stop_service
    
    # 禁用服务
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    
    # 删除服务文件
    rm -f "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
    
    # 删除安装目录
    rm -rf "$INSTALL_DIR"
    
    log_info "Uninstallation completed"
}

show_status() {
    log_info "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager -l || true
    
    log_info "Recent logs:"
    journalctl -u "$SERVICE_NAME" --no-pager -l -n 20 || true
}

show_help() {
    echo "Usage: $0 {install|start|stop|restart|status|uninstall|test}"
    echo ""
    echo "Commands:"
    echo "  install   - Install Impala Monitor"
    echo "  start     - Start the service"
    echo "  stop      - Stop the service"
    echo "  restart   - Restart the service"
    echo "  status    - Show service status and logs"
    echo "  uninstall - Remove Impala Monitor"
    echo "  test      - Test the installation"
    echo ""
}

test_installation() {
    log_info "Testing installation..."
    
    # 检查文件
    if [[ -f "$INSTALL_DIR/src/impala_monitor.py" ]]; then
        log_info "✓ Monitor script found"
    else
        log_error "✗ Monitor script not found"
        return 1
    fi
    
    # 检查配置
    if [[ -f "$INSTALL_DIR/config/node_config.yaml" ]]; then
        log_info "✓ Configuration file found"
    else
        log_error "✗ Configuration file not found"
        return 1
    fi
    
    # 检查服务
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log_info "✓ Service is enabled"
    else
        log_warn "✗ Service is not enabled"
    fi
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "✓ Service is running"
    else
        log_warn "✗ Service is not running"
    fi
    
    # 测试 Python 脚本
    log_info "Testing Python script..."
    cd "$INSTALL_DIR/src"
    if python3 -c "import impala_exporter, impala_monitor; print('✓ Python modules import successfully')"; then
        log_info "✓ Python modules are working"
    else
        log_error "✗ Python modules have issues"
        return 1
    fi
    
    log_info "Installation test completed"
}

# 主逻辑
case "${1:-}" in
    install)
        check_root
        install_dependencies
        install_files
        create_systemd_service
        configure_firewall
        start_service
        log_info "Installation completed successfully!"
        log_info "You can check the status with: $0 status"
        ;;
    start)
        check_root
        start_service
        ;;
    stop)
        check_root
        stop_service
        ;;
    restart)
        check_root
        stop_service
        start_service
        ;;
    status)
        show_status
        ;;
    uninstall)
        check_root
        uninstall
        ;;
    test)
        test_installation
        ;;
    *)
        show_help
        exit 1
        ;;
esac
