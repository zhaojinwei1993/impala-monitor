#!/bin/bash
"""
Impala Monitor 卸载脚本
用于从多个节点卸载 Impala 监控采集程序
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLAYBOOK_DIR="$ANSIBLE_DIR/playbooks"
INVENTORY_DIR="$ANSIBLE_DIR/inventory"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # 检查 Ansible
    if ! command -v ansible-playbook &> /dev/null; then
        log_error "Ansible is not installed. Please install Ansible first."
        exit 1
    fi
    
    # 检查 inventory 文件
    if [[ ! -f "$INVENTORY_DIR/inventory.ini" ]]; then
        log_error "Inventory file not found: $INVENTORY_DIR/inventory.ini"
        log_info "Please create the inventory file first."
        exit 1
    fi
    
    # 检查 playbook 文件
    if [[ ! -f "$PLAYBOOK_DIR/uninstall-impala-monitor.yml" ]]; then
        log_error "Playbook file not found: $PLAYBOOK_DIR/uninstall-impala-monitor.yml"
        exit 1
    fi
    
    log_info "✓ All requirements satisfied"
}

show_inventory() {
    log_info "Current inventory configuration:"
    echo "----------------------------------------"
    cat "$INVENTORY_DIR/inventory.ini"
    echo "----------------------------------------"
}

confirm_uninstall() {
    log_warn "This will COMPLETELY REMOVE Impala Monitor from all nodes in the inventory!"
    log_warn "The following will be removed:"
    echo "  - Impala Monitor services (both original and V2)"
    echo "  - Installation directory (/opt/impala-monitor)"
    echo "  - System user (impala-monitor)"
    echo "  - Firewall rules"
    echo "  - Service files"
    echo ""
    log_info "Configuration will be backed up to /tmp/ before removal."
    echo ""
    
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "Uninstallation cancelled."
        exit 0
    fi
}

run_uninstall() {
    log_info "Starting uninstallation process..."
    
    local extra_vars=""
    local tags=""
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --remove-packages)
                tags="--tags remove_packages"
                log_info "Will also remove Python packages"
                shift
                ;;
            --limit)
                extra_vars="$extra_vars --limit $2"
                log_info "Limiting to hosts: $2"
                shift 2
                ;;
            --dry-run)
                extra_vars="$extra_vars --check"
                log_info "Running in dry-run mode"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 执行 Ansible playbook
    log_info "Executing Ansible playbook..."
    
    ansible-playbook \
        -i "$INVENTORY_DIR/inventory.ini" \
        "$PLAYBOOK_DIR/uninstall-impala-monitor.yml" \
        $extra_vars \
        $tags \
        -v
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_info "✓ Uninstallation completed successfully!"
        log_info "Configuration backups are available in /tmp/ on each node"
    else
        log_error "✗ Uninstallation failed with exit code: $exit_code"
        exit $exit_code
    fi
}

verify_uninstall() {
    log_info "Verifying uninstallation..."
    
    # 创建验证 playbook
    cat > "/tmp/verify-uninstall.yml" << 'EOF'
---
- name: Verify Impala Monitor Uninstallation
  hosts: impala_nodes
  gather_facts: no
  tasks:
    - name: Check if services exist
      command: systemctl list-unit-files --type=service
      register: services
      changed_when: false
      
    - name: Check if installation directory exists
      stat:
        path: /opt/impala-monitor
      register: install_dir
      
    - name: Check if user exists
      getent:
        database: passwd
        key: impala-monitor
      register: user_check
      ignore_errors: yes
      
    - name: Display verification results
      debug:
        msg: |
          Host: {{ inventory_hostname }}
          Services removed: {{ 'impala-monitor' not in services.stdout }}
          Directory removed: {{ not install_dir.stat.exists }}
          User removed: {{ user_check is failed }}
EOF

    ansible-playbook \
        -i "$INVENTORY_DIR/inventory.ini" \
        "/tmp/verify-uninstall.yml" \
        -v
    
    rm -f "/tmp/verify-uninstall.yml"
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Uninstall Impala Monitor from multiple nodes using Ansible"
    echo ""
    echo "Options:"
    echo "  --remove-packages    Also remove Python packages (prometheus-client, etc.)"
    echo "  --limit HOSTS        Limit uninstallation to specific hosts"
    echo "  --dry-run           Run in check mode (no actual changes)"
    echo "  --verify            Only run verification (check if already uninstalled)"
    echo "  --show-inventory    Show current inventory configuration"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Uninstall from all nodes"
    echo "  $0 --limit node1,node2               # Uninstall from specific nodes"
    echo "  $0 --remove-packages                 # Also remove Python packages"
    echo "  $0 --dry-run                         # Check what would be removed"
    echo "  $0 --verify                          # Verify uninstallation"
    echo ""
}

# 主逻辑
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --show-inventory)
        show_inventory
        exit 0
        ;;
    --verify)
        check_requirements
        verify_uninstall
        exit 0
        ;;
    *)
        # 正常卸载流程
        check_requirements
        show_inventory
        confirm_uninstall
        run_uninstall "$@"
        
        # 询问是否验证
        echo ""
        read -p "Do you want to verify the uninstallation? (y/n): " verify_choice
        if [[ "$verify_choice" =~ ^[Yy] ]]; then
            verify_uninstall
        fi
        
        log_info "Uninstallation process completed!"
        ;;
esac
