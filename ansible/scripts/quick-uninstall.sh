#!/bin/bash
"""
快速卸载脚本
用于紧急情况下快速卸载 Impala Monitor
"""

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 解析命令行参数
HOSTS=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --hosts)
            HOSTS="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 --hosts 'host1,host2,host3' [--force]"
            echo ""
            echo "Options:"
            echo "  --hosts HOSTS    Comma-separated list of hosts"
            echo "  --force          Skip confirmation"
            echo "  --help           Show this help"
            echo ""
            echo "Example:"
            echo "  $0 --hosts 'node1,node2,node3'"
            echo "  $0 --hosts 'root@192.168.1.101,root@192.168.1.102' --force"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$HOSTS" ]]; then
    log_error "Please specify hosts with --hosts option"
    exit 1
fi

# 转换主机列表
IFS=',' read -ra HOST_ARRAY <<< "$HOSTS"

log_info "Target hosts: ${HOST_ARRAY[*]}"

if [[ "$FORCE" != "true" ]]; then
    log_warn "This will quickly uninstall Impala Monitor from all specified hosts!"
    read -p "Continue? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "Cancelled."
        exit 0
    fi
fi

# 创建临时卸载脚本
TEMP_SCRIPT="/tmp/impala-monitor-uninstall.sh"
cat > "$TEMP_SCRIPT" << 'EOF'
#!/bin/bash
set -e

echo "Uninstalling Impala Monitor on $(hostname)..."

# 停止服务
sudo systemctl stop impala-monitor 2>/dev/null || true
sudo systemctl stop impala-monitor-v2 2>/dev/null || true

# 禁用服务
sudo systemctl disable impala-monitor 2>/dev/null || true
sudo systemctl disable impala-monitor-v2 2>/dev/null || true

# 删除服务文件
sudo rm -f /etc/systemd/system/impala-monitor.service
sudo rm -f /etc/systemd/system/impala-monitor-v2.service

# 重新加载 systemd
sudo systemctl daemon-reload

# 备份配置
if [[ -d /opt/impala-monitor/config ]]; then
    sudo cp -r /opt/impala-monitor/config /tmp/impala-monitor-backup-$(date +%s) 2>/dev/null || true
fi

# 删除安装目录
sudo rm -rf /opt/impala-monitor

# 删除用户
sudo userdel impala-monitor 2>/dev/null || true

# 删除防火墙规则
if command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --remove-port=9356/tcp 2>/dev/null || true
    sudo firewall-cmd --permanent --remove-port=9357/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
elif command -v ufw &> /dev/null; then
    sudo ufw delete allow 9356/tcp 2>/dev/null || true
    sudo ufw delete allow 9357/tcp 2>/dev/null || true
fi

# 清理日志
sudo rm -f /var/log/impala-monitor*.log

echo "✓ Uninstallation completed on $(hostname)"
EOF

chmod +x "$TEMP_SCRIPT"

# 执行卸载
success_count=0
failed_hosts=()

for host in "${HOST_ARRAY[@]}"; do
    log_info "Uninstalling from $host..."
    
    if scp "$TEMP_SCRIPT" "$host:/tmp/" && ssh "$host" "bash /tmp/impala-monitor-uninstall.sh && rm -f /tmp/impala-monitor-uninstall.sh"; then
        log_info "✓ Successfully uninstalled from $host"
        ((success_count++))
    else
        log_error "✗ Failed to uninstall from $host"
        failed_hosts+=("$host")
    fi
done

# 清理临时脚本
rm -f "$TEMP_SCRIPT"

# 显示结果
echo ""
log_info "Uninstallation Summary:"
log_info "  Successful: $success_count/${#HOST_ARRAY[@]}"

if [[ ${#failed_hosts[@]} -gt 0 ]]; then
    log_error "  Failed hosts: ${failed_hosts[*]}"
    exit 1
else
    log_info "  All hosts completed successfully!"
fi
