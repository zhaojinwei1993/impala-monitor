#!/bin/bash
"""
测试root用户连接脚本
验证Ansible能否使用root用户连接到目标主机
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY_FILE="$SCRIPT_DIR/../inventory/inventory.ini"

echo "测试root用户连接..."
echo "使用inventory文件: $INVENTORY_FILE"

if [[ ! -f "$INVENTORY_FILE" ]]; then
    echo "错误: inventory文件不存在: $INVENTORY_FILE"
    exit 1
fi

echo "执行连接测试..."
ansible impala_nodes -i "$INVENTORY_FILE" -u root -m ping

echo ""
echo "如果上面显示SUCCESS，说明root用户连接正常"
echo "现在可以使用以下命令进行部署/卸载："
echo ""
echo "部署:"
echo "  ./deploy.sh"
echo ""
echo "卸载:"
echo "  ./uninstall.sh"
echo ""
echo "快速卸载:"
echo "  ./quick-uninstall.sh --hosts 'host1,host2,host3'"
