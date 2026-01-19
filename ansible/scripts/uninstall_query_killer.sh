#!/bin/bash
# 批量卸载 Impala Query Killer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Uninstalling Impala Query Killer from all nodes..."

cd "$ANSIBLE_DIR"

ansible-playbook \
    -i inventory/inventory.ini \
    uninstall_query_killer.yml

echo ""
echo "Uninstallation completed!"
