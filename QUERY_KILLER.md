# Impala Query Killer 使用说明

自动监控并终止超时或超内存的 Impala 查询，并通过飞书通知相关人员。

## 目录
- [架构说明](#架构说明)
- [工作流程](#工作流程)
- [部署方式](#部署方式)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [卸载](#卸载)
- [故障排查](#故障排查)

## 架构说明

```
┌─────────────────────────────────────────────────────────────────┐
│                      Impala 集群架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Node 1      │    │  Node 2      │    │  Node 3      │      │
│  │ 10.19.20.238 │    │ 10.19.20.239 │    │ 10.19.20.240 │      │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤      │
│  │ Impalad      │    │ Impalad      │    │ Impalad      │      │
│  │ :25000       │    │ :25000       │    │ :25000       │      │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤      │
│  │ Query Killer │    │ Query Killer │    │ Query Killer │      │
│  │   ↓          │    │   ↓          │    │   ↓          │      │
│  │ 监控本节点    │    │ 监控本节点    │    │ 监控本节点    │      │
│  │ Kill 本节点   │    │ Kill 本节点   │    │ Kill 本节点   │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             ↓                                    │
│                    ┌─────────────────┐                          │
│                    │  飞书机器人      │                          │
│                    │  统一接收通知    │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 核心特性

- ⏱️ **超时检测**：自动 kill 运行超过阈值的查询（默认 10 分钟）
- 💾 **内存检测**：自动 kill 内存使用超过阈值的查询（默认 1TB）
- 📢 **飞书通知**：终止查询后自动发送详细信息到飞书群
- 🔄 **持续监控**：后台服务持续运行，定期检查（默认 60 秒）
- 🏠 **本地执行**：每个节点监控并终止本节点的查询
- 🛡️ **智能验证**：超时后验证查询是否真的被终止

### 为什么每个节点都要部署？

由于 Impala 的安全限制，每个节点的 25000 端口只能在本地访问，因此：
- **必须在每个 Impala 节点上部署 Query Killer**
- 每个节点的 Query Killer 只监控和终止本节点的查询
- 所有节点共享同一个飞书 webhook，通知中会显示节点信息

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Query Killer 工作流程                          │
└─────────────────────────────────────────────────────────────────┘

1. 启动服务
   ↓
2. 读取配置文件 (/opt/impala-monitor/config/query_killer.conf)
   ↓
3. 每隔 CHECK_INTERVAL 秒执行一次检查
   ↓
4. 调用 Impala Web UI (http://本机IP:25000/queries?json)
   ↓
5. 获取所有 RUNNING 状态的查询
   ↓
6. 检查每个查询：
   ├─ 运行时间 > MAX_DURATION？
   ├─ 内存使用 > MAX_MEMORY_GB？
   └─ 跳过系统查询（GET_SCHEMAS 等）
   ↓
7. 如果超标：
   ├─ 发送 cancel 请求 (http://本机IP:25000/cancel_query?query_id=xxx)
   ├─ 如果超时：等待 5 秒后验证查询是否还在运行
   └─ 如果成功：发送飞书通知
   ↓
8. 记录日志到 /opt/impala-monitor/logs/query_killer.log
   ↓
9. 返回步骤 3
```

## 部署方式

### 前提条件

1. **已部署 impala-monitor**：Query Killer 依赖 impala-monitor 的文件
   ```bash
   # 如果还没部署，先部署 impala-monitor
   cd ansible/scripts
   ./deploy.sh
   ```

2. **创建飞书机器人**：
   - 在飞书群中添加自定义机器人
   - 设置关键字：`query-killer`
   - 复制 webhook 地址

### 方式一：批量部署（推荐）

适用于多节点集群，使用 Ansible 自动部署到所有节点。

```bash
# 1. 设置飞书 webhook
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 2. 可选：自定义阈值
export MAX_DURATION=600        # 默认 600 秒（10 分钟）
export MAX_MEMORY_GB=1024      # 默认 1024 GB（1TB）
export CHECK_INTERVAL=60       # 默认 60 秒

# 3. 执行批量部署
cd ansible/scripts
./deploy_query_killer.sh

# 4. 验证部署
ansible impala_nodes -i ../inventory/inventory.ini -m shell -a 'systemctl status impala-query-killer'
```

### 方式二：单节点部署

适用于单个节点或手动部署。

```bash
# 1. 创建配置目录
sudo mkdir -p /opt/impala-monitor/config

# 2. 复制配置文件模板
sudo cp monitor/config/query_killer.conf /opt/impala-monitor/config/

# 3. 编辑配置文件
sudo vim /opt/impala-monitor/config/query_killer.conf
```

配置文件示例：
```bash
# Impala 连接配置
IMPALA_HOST=10.19.20.238        # 填写本机 IP
IMPALA_PORT=25000

# 飞书通知配置
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# 检查间隔（秒）
CHECK_INTERVAL=60

# 查询阈值配置
MAX_DURATION=600                # 10 分钟
MAX_MEMORY_GB=1024              # 1TB
```

```bash
# 4. 执行部署
cd monitor/scripts
sudo ./deploy_query_killer.sh install

# 5. 验证部署
sudo systemctl status impala-query-killer
```

### 方式三：手动测试（开发/调试）

```bash
# 1. 准备配置文件（同方式二）

# 2. 前台运行（方便查看日志）
cd monitor/src
sudo python3 query_killer.py --config /opt/impala-monitor/config/query_killer.conf

# 或者使用命令行参数（覆盖配置文件）
sudo python3 query_killer.py \
    --host 10.19.20.238 \
    --feishu-webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" \
    --max-duration 600 \
    --max-memory-gb 1024
```

## 配置说明

### 配置文件位置
- **生产环境**：`/opt/impala-monitor/config/query_killer.conf`
- **模板文件**：`monitor/config/query_killer.conf`

### 配置参数

| 参数 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `IMPALA_HOST` | Impala 节点 IP 地址 | - | ✓ |
| `IMPALA_PORT` | Impala Web UI 端口 | 25000 | |
| `FEISHU_WEBHOOK` | 飞书机器人 webhook 地址 | - | ✓ |
| `CHECK_INTERVAL` | 检查间隔（秒） | 60 | |
| `MAX_DURATION` | 最大运行时间（秒） | 600 | |
| `MAX_MEMORY_GB` | 最大内存（GB） | 1024 | |

### 修改配置

```bash
# 1. 编辑配置文件
sudo vim /opt/impala-monitor/config/query_killer.conf

# 2. 重启服务使配置生效
sudo systemctl restart impala-query-killer

# 3. 查看日志确认
sudo tail -f /opt/impala-monitor/logs/query_killer.log
```

## 服务管理

### 查看服务状态
```bash
sudo systemctl status impala-query-killer
```

### 启动服务
```bash
sudo systemctl start impala-query-killer
```

### 停止服务
```bash
sudo systemctl stop impala-query-killer
```

### 重启服务
```bash
sudo systemctl restart impala-query-killer
# 或使用部署脚本
cd monitor/scripts
sudo ./deploy_query_killer.sh restart
```

### 查看日志
```bash
# 实时查看日志
sudo tail -f /opt/impala-monitor/logs/query_killer.log

# 查看最近 100 行
sudo tail -n 100 /opt/impala-monitor/logs/query_killer.log

# 查看 systemd 日志
sudo journalctl -u impala-query-killer -f
```

### 开机自启
```bash
# 启用开机自启（部署时已自动启用）
sudo systemctl enable impala-query-killer

# 禁用开机自启
sudo systemctl disable impala-query-killer
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

### 手动卸载

```bash
# 1. 停止并禁用服务
sudo systemctl stop impala-query-killer
sudo systemctl disable impala-query-killer

# 2. 删除服务文件
sudo rm -f /etc/systemd/system/impala-query-killer.service

# 3. 删除程序文件（保留日志）
sudo rm -f /opt/impala-monitor/src/query_killer.py
sudo rm -f /opt/impala-monitor/config/query_killer.conf

# 4. 重新加载 systemd
sudo systemctl daemon-reload
```

## 飞书通知格式

当查询被终止时，会发送以下格式的通知：

```
⚠️ query-killer: Impala 查询已被自动终止

节点：10.19.20.238
查询用户：username
查询 query_id：a644db6140054bf9:88227ede00000000
查询时间：2026-01-19 14:23:50
运行时长：12.5 分钟
查询内存：1024.50 GB
终止原因：运行时间超过 10 分钟

该 SQL 运行时间/占用内存过大影响到集群稳定性，请优化代码或者使用 hive on spark 进行查询。
```

## 故障排查

### 1. 服务无法启动

**检查配置文件**
```bash
# 查看配置文件是否存在
ls -l /opt/impala-monitor/config/query_killer.conf

# 检查配置内容
sudo cat /opt/impala-monitor/config/query_killer.conf
```

**查看详细错误**
```bash
sudo journalctl -u impala-query-killer -n 50
sudo tail -n 50 /opt/impala-monitor/logs/query_killer.log
```

### 2. 无法连接 Impala

**测试连接**
```bash
# 测试 Impala Web UI
curl http://10.19.20.238:25000/queries?json

# 检查 Impala 进程
ps aux | grep impalad
```

**检查防火墙**
```bash
# 检查 25000 端口是否开放
sudo netstat -tlnp | grep 25000
```

### 3. 飞书通知未收到

**测试飞书 webhook**
```bash
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"⚠️ query-killer: 测试消息"}}'
```

**检查日志**
```bash
# 查找飞书相关日志
sudo grep -i feishu /opt/impala-monitor/logs/query_killer.log
```

**常见问题**
- 确认 webhook 地址正确
- 确认机器人关键字设置为 `query-killer`
- 确认网络可以访问飞书 API

### 4. 查询未被 kill

**检查阈值配置**
```bash
# 查看当前配置
sudo cat /opt/impala-monitor/config/query_killer.conf

# 查看日志中的阈值信息
sudo grep "Max duration\|Max memory" /opt/impala-monitor/logs/query_killer.log
```

**手动测试 cancel**
```bash
# 获取查询 ID
curl http://10.19.20.238:25000/queries?json | grep query_id

# 手动 cancel
curl "http://10.19.20.238:25000/cancel_query?query_id=YOUR_QUERY_ID"
```

### 5. Cancel 请求超时

这是正常现象，Query Killer 会：
1. 等待 5 秒
2. 验证查询是否还在运行
3. 如果查询已终止，仍然发送飞书通知

**查看验证日志**
```bash
sudo grep "Waiting 5 seconds\|no longer running" /opt/impala-monitor/logs/query_killer.log
```

## 注意事项

1. ✓ **必须在每个 Impala 节点上部署**：因为 25000 端口只能本地访问
2. ✓ **先部署 impala-monitor**：Query Killer 依赖其文件和依赖
3. ✓ **使用 root 用户部署**：需要创建 systemd 服务
4. ✓ **飞书机器人关键字**：必须设置为 `query-killer`
5. ✓ **配置文件优先**：所有配置从配置文件读取，便于管理
6. ✓ **测试后再上线**：建议先在测试环境验证
7. ✓ **调整阈值**：根据实际情况调整超时和内存阈值
8. ✓ **系统查询跳过**：自动跳过 `GET_SCHEMAS` 等系统查询

## 文件结构

```
/opt/impala-monitor/
├── config/
│   └── query_killer.conf          # 配置文件
├── src/
│   ├── query_killer.py            # 主程序
│   └── impala_exporter.py         # Impala 数据采集（复用）
├── logs/
│   └── query_killer.log           # 运行日志
└── requirements.txt               # Python 依赖（复用）

/etc/systemd/system/
└── impala-query-killer.service    # systemd 服务文件
```

## 相关文档

- [Impala Monitor 部署文档](DEPLOY.md)
- [Impala Monitor 主文档](README.md)

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
