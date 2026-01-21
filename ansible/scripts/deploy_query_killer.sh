#!/bin/bash
# 批量部署 Impala Query Killer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 检查参数
if [ -z "$FEISHU_WEBHOOK" ]; then
    echo "Error: FEISHU_WEBHOOK environment variable is required"
    echo ""
    echo "Usage:"
    echo "  export FEISHU_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'"
    echo "  $0"
    exit 1
fi

# 可选参数
MAX_DURATION="${MAX_DURATION:-600}"
MAX_MEMORY_GB="${MAX_MEMORY_GB:-1024}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

echo "Deploying Impala Query Killer to all nodes..."
echo "Configuration:"
echo "  Feishu Webhook: ${FEISHU_WEBHOOK:0:50}..."
echo "  Max Duration: ${MAX_DURATION}s"
echo "  Max Memory: ${MAX_MEMORY_GB}GB"
echo "  Check Interval: ${CHECK_INTERVAL}s"
echo ""

cd "$ANSIBLE_DIR"

ansible-playbook \
    -i inventory/inventory.ini \
    -u root \
    deploy_query_killer.yml \
    -e "feishu_webhook=$FEISHU_WEBHOOK" \
    -e "max_duration=$MAX_DURATION" \
    -e "max_memory_gb=$MAX_MEMORY_GB" \
    -e "check_interval=$CHECK_INTERVAL"

echo ""
echo "Deployment completed!"
echo ""
echo "Check status on all nodes:"
echo "  ansible impala_nodes -i inventory/inventory.ini -m shell -u root -a 'systemctl status impala-query-killer'"
