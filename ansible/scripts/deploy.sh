#!/bin/bash

# Impala Monitor 自动化部署脚本

echo "开始部署 Impala Monitor..."

# 检查 Ansible 是否安装
if ! command -v ansible-playbook &> /dev/null; then
    echo "错误: 未找到 ansible-playbook，请先安装 Ansible"
    exit 1
fi

# 检查 inventory 文件
if [ ! -f "../inventory/inventory.ini" ]; then
    echo "错误: 未找到 inventory.ini 文件，请先配置目标主机"
    exit 1
fi

# 执行部署
ansible-playbook -i ../inventory/inventory.ini -u root ../playbooks/deploy-impala-monitor.yml

echo "部署完成！"
echo "可以通过以下命令检查服务状态："
echo "ansible impala_nodes -i ../inventory/inventory.ini -u root -m shell -a 'systemctl status impala-monitor'"
