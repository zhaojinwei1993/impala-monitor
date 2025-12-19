# Impala Monitor

Apache Impala 集群监控解决方案，提供节点级别的指标采集和 Grafana 可视化。

## 功能特性

- 🔍 **自动指标采集**：采集 Impala 节点的内存、CPU、查询等关键指标
- 📊 **Prometheus 集成**：标准 Prometheus 指标格式导出
- 📈 **Grafana 仪表板**：预配置的监控面板
- 🚀 **自动部署**：Ansible 一键部署
- 🏷️ **主机标签**：支持主机IP和主机名标签，便于多节点管理
- 📋 **查询详情**：采集每个查询的详细信息（用户、内存、执行时间等）

## 快速开始

### 单节点部署
```bash
# 1. 克隆仓库
git clone https://github.com/zhaojinwei1993/impala-monitor.git
cd impala-monitor

# 2. 安装依赖
pip3 install -r monitor/requirements.txt

# 3. 运行监控
python3 monitor/src/impala_monitor.py --host <impala_host>

# 4. 验证运行
curl http://localhost:9356/metrics
```

### 服务化部署
```bash
cd monitor/scripts
sudo ./deploy_node_collector.sh install
```

### 批量部署
```bash
# 1. 配置主机清单
vim ansible/inventory/inventory.ini

# 2. 执行部署
cd ansible/scripts && ./deploy.sh
```

## 监控指标

### 核心指标（带主机标签）
- **内存使用**：进程限制、RSS、总使用量
- **JVM 指标**：堆内存、非堆内存、GC 时间
- **查询状态**：执行中、等待、总数量
- **会话连接**：Beeswax、HiveServer2 会话数

### 查询详情指标
每个查询包含以下信息：
- `impala_query_memory_usage_bytes` - 内存使用量
- `impala_query_duration_seconds` - 执行时间
- `impala_query_start_time` - 开始时间戳
- `impala_query_end_time` - 结束时间戳
- `impala_query_info` - 查询语句信息（SQL语句）

标签：`host_ip`, `hostname`, `query_id`, `effective_user`, `state`

## Grafana 仪表板

导入 `monitor/grafana-impala-dashboard.json`，支持：
- 主机过滤器：选择特定主机或查看所有主机
- 按主机分组的图表
- 查询详情表格：显示正在执行的查询信息
- 内存和 JVM 趋势图

## 卸载

### 单节点卸载
```bash
cd monitor/scripts
sudo ./deploy_node_collector.sh uninstall
```

### 批量卸载
```bash
# 配置要卸载的主机清单
vim ansible/inventory/cleanup-inventory.ini

# 执行批量卸载
cd ansible/scripts
./uninstall.sh
```

### 手动卸载
```bash
# 停止服务
sudo systemctl stop impala-monitor
sudo systemctl disable impala-monitor

# 删除服务文件
sudo rm -f /etc/systemd/system/impala-monitor.service

# 删除程序文件
sudo rm -rf /opt/impala-monitor

# 重新加载 systemd
sudo systemctl daemon-reload
```

## 详细部署指南

查看 [DEPLOY.md](DEPLOY.md) 获取完整的部署说明。

## 许可证

MIT License
