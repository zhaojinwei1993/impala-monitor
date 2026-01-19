# Impala Query Killer 使用说明

自动监控并终止超时或超内存的 Impala 查询，并通过飞书通知相关人员。

## 功能特性

- ⏱️ **超时检测**：自动 kill 运行超过 10 分钟的查询
- 💾 **内存检测**：自动 kill 内存使用超过 1TB 的查询
- 📢 **飞书通知**：终止查询后自动发送详细信息到飞书群
- 🔄 **持续监控**：后台服务持续运行，定期检查
- 🏠 **本地执行**：每个节点监控并终止本节点的查询（因为 Impala 25000 端口只能本地访问）

## 架构说明

由于 Impala 集群的安全限制，每个节点的 25000 端口只能在本地访问，因此：
- **必须在每个 Impala 节点上部署 Query Killer**
- 每个节点的 Query Killer 只监控和终止本节点的查询
- 使用 `localhost` 连接本地 Impala 进程

## 快速部署

### 批量部署（推荐）

```bash
# 1. 设置飞书 webhook（必需）
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 2. 可选配置
export CHECK_INTERVAL=60        # 检查间隔（秒），默认 60
export MAX_DURATION=600         # 最大运行时间（秒），默认 600（10分钟）
export MAX_MEMORY_GB=1024       # 最大内存（GB），默认 1024（1TB）

# 3. 执行批量部署
cd ansible/scripts
./deploy_query_killer.sh
```

**前提条件**：
- 已经使用 `ansible/scripts/deploy.sh` 部署了 impala-monitor
- Query Killer 会复用已安装的依赖和 impala_exporter.py

### 单节点部署

```bash
# 设置环境变量
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 可选配置
export CHECK_INTERVAL=60
export MAX_DURATION=600
export MAX_MEMORY_GB=1024

# 执行部署（会自动使用 localhost）
cd monitor/scripts
sudo -E ./deploy_query_killer.sh install
```

### 手动运行（测试）

```bash
cd monitor/src
python3 query_killer.py \
    --host localhost \
    --feishu-webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" \
    --check-interval 60 \
    --max-duration 600 \
    --max-memory-gb 1024
```

## 服务管理

```bash
# 查看服务状态
sudo systemctl status impala-query-killer

# 重启服务
sudo systemctl restart impala-query-killer

# 停止服务
sudo systemctl stop impala-query-killer

# 查看日志
sudo tail -f /opt/impala-monitor/logs/query_killer.log
```

## 卸载

### 批量卸载

```bash
cd ansible/scripts
./uninstall_query_killer.sh
```

### 单节点卸载

```bash
cd monitor/scripts
sudo ./deploy_query_killer.sh uninstall
```

## 飞书通知格式

当查询被终止时，会发送以下格式的通知：

```
⚠️ query-killer: Impala 查询已被自动终止

节点：10.19.20.238
查询用户：username
查询 query_id：query_id_here
查询时间：2026-01-19 14:23:50
运行时长：12.5 分钟
查询内存：1024.50 GB
终止原因：运行时间超过 10 分钟

该 SQL 运行时间/占用内存过大影响到集群稳定性，请优化代码或者使用 hive on spark 进行查询。
```

## 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--host` | Impala 主机地址 | 必填 |
| `--port` | Impala 端口 | 25000 |
| `--feishu-webhook` | 飞书 webhook 地址 | 可选 |
| `--check-interval` | 检查间隔（秒） | 60 |
| `--max-duration` | 最大运行时间（秒） | 600 |
| `--max-memory-gb` | 最大内存（GB） | 1024 |

## 注意事项

1. 确保运行脚本的机器可以访问 Impala 的 Web UI（默认 25000 端口）
2. 飞书 webhook 地址需要提前在飞书群中创建
3. 建议先在测试环境验证后再部署到生产环境
4. 可以根据实际情况调整超时和内存阈值
5. 服务会自动跳过 `GET_SCHEMAS` 等系统查询

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
sudo journalctl -u impala-query-killer -n 50

# 检查配置
sudo systemctl cat impala-query-killer
```

### 无法连接 Impala

```bash
# 测试连接
curl http://your-impala-host:25000/queries?json
```

### 飞书通知未收到

1. 检查 webhook 地址是否正确
2. 确认网络可以访问飞书 API
3. 查看日志中是否有发送失败的错误信息
