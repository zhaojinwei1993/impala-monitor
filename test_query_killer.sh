#!/bin/bash
# Query Killer 单节点测试脚本

set -e

# 配置参数
IMPALA_HOST="${IMPALA_HOST:-}"
FEISHU_WEBHOOK="${FEISHU_WEBHOOK:-}"
IMPALA_PORT="${IMPALA_PORT:-25000}"

echo "=========================================="
echo "Query Killer 测试脚本"
echo "=========================================="
echo ""

# 检查 Impala host
if [ -z "$IMPALA_HOST" ]; then
    echo "❌ 错误：请设置 IMPALA_HOST 环境变量"
    echo ""
    echo "使用方法："
    echo "  export IMPALA_HOST='10.19.20.238'"
    echo "  export FEISHU_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'"
    echo "  bash test_query_killer.sh"
    exit 1
fi

# 检查飞书 webhook
if [ -z "$FEISHU_WEBHOOK" ]; then
    echo "❌ 错误：请设置 FEISHU_WEBHOOK 环境变量"
    echo ""
    echo "使用方法："
    echo "  export IMPALA_HOST='10.19.20.238'"
    echo "  export FEISHU_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/xxx'"
    echo "  bash test_query_killer.sh"
    exit 1
fi

echo "✓ Impala Host: $IMPALA_HOST"
echo "✓ 飞书 Webhook: ${FEISHU_WEBHOOK:0:50}..."
echo ""

# 1. 测试 Impala 连接
echo "1. 测试 Impala 连接..."
if curl -s http://${IMPALA_HOST}:${IMPALA_PORT}/queries?json > /dev/null; then
    echo "   ✓ Impala 连接成功"
else
    echo "   ❌ Impala 连接失败，请检查 Impala 是否运行"
    exit 1
fi
echo ""

# 2. 测试飞书通知
echo "2. 测试飞书通知..."
cat > /tmp/test_feishu.json <<EOF
{
  "msg_type": "text",
  "content": {
    "text": "⚠️ query-killer: 测试消息\n\n这是一条测试消息，如果收到说明配置正确。"
  }
}
EOF

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$FEISHU_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d @/tmp/test_feishu.json)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✓ 飞书通知发送成功"
    echo "   响应: $BODY"
else
    echo "   ❌ 飞书通知发送失败 (HTTP $HTTP_CODE)"
    echo "   响应: $BODY"
    exit 1
fi
rm -f /tmp/test_feishu.json
echo ""

# 3. 运行 Query Killer（前台运行 2 分钟）
echo "3. 启动 Query Killer（前台运行 2 分钟用于测试）..."
echo "   按 Ctrl+C 可随时停止"
echo ""

cd monitor/src
timeout 120 python3 query_killer.py \
    --host ${IMPALA_HOST} \
    --port ${IMPALA_PORT} \
    --feishu-webhook "$FEISHU_WEBHOOK" \
    --check-interval 30 \
    --max-duration 600 \
    --max-memory-gb 1024 \
    || true

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "如果一切正常，可以使用以下命令部署为服务："
echo "  export IMPALA_HOST='$IMPALA_HOST'"
echo "  export FEISHU_WEBHOOK='$FEISHU_WEBHOOK'"
echo "  cd monitor/scripts"
echo "  sudo -E ./deploy_query_killer.sh install"
