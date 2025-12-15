#!/bin/bash

# 读取 Impala 节点地址文件，生成 Prometheus 配置

NODES_FILE="impala-nodes.txt"
OUTPUT_FILE="prometheus-impala.yml"

if [ ! -f "$NODES_FILE" ]; then
    echo "错误: 未找到 $NODES_FILE 文件"
    exit 1
fi

# 生成 Prometheus 配置文件
cat > "$OUTPUT_FILE" << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'impala-nodes'
    static_configs:
      - targets:
EOF

# 添加节点地址
while IFS= read -r node; do
    if [ ! -z "$node" ] && [[ ! "$node" =~ ^# ]]; then
        echo "          - '$node:9356'" >> "$OUTPUT_FILE"
    fi
done < "$NODES_FILE"

# 添加其他配置
cat >> "$OUTPUT_FILE" << 'EOF'
    scrape_interval: 30s
    metrics_path: /metrics
EOF

echo "Prometheus 配置已生成到 $OUTPUT_FILE"
echo "节点数量: $(grep -v '^#' $NODES_FILE | grep -v '^$' | wc -l)"
