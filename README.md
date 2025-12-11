# Impala Monitor

Apache Impala 集群监控解决方案，提供节点级别的指标采集和 Grafana 可视化。

## 功能特性

- 🔍 **自动指标采集**：采集 Impala 节点的内存、CPU、查询等关键指标
- 📊 **Prometheus 集成**：标准 Prometheus 指标格式导出
- 📈 **Grafana 仪表板**：预配置的监控面板
- 🚀 **自动部署**：一键部署脚本
- 🔧 **智能配置**：自动获取网卡 IP 地址

## 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/你的用户名/impala-monitor.git
cd impala-monitor
```

### 2. 安装依赖
```bash
pip3 install -r requirements.txt
```

### 3. 运行采集器
```bash
# 自动获取 IP 并启动
python3 impala_node_collector.py

# 或者一键部署为系统服务
sudo ./deploy_node_collector.sh install
```

### 4. 验证运行
```bash
# 检查指标
curl http://localhost:9356/metrics

# 导入 Grafana 仪表板
# 使用 grafana-impala-node-dashboard.json
```

## 项目结构

```
impala-monitor/
├── README.md                           # 项目说明
├── impala_node_collector.py           # 主采集器程序
├── node_config.yaml                   # 配置文件
├── requirements.txt                   # Python 依赖
├── deploy_node_collector.sh           # 部署脚本
├── get_ip.py                          # IP 获取测试工具
├── grafana-impala-node-dashboard.json # Grafana 仪表板
└── README_NODE_COLLECTOR.md           # 详细文档
```

## 监控指标

### 核心指标
- **内存使用**：RSS、TCMalloc、JVM 堆内存
- **查询状态**：执行中、等待、排队查询数量
- **查询性能**：执行时间、内存使用分布
- **系统资源**：线程数、连接数、I/O 吞吐

### 查询详情
- 实时查询列表（用户、SQL、内存使用、运行时间）
- 资源占用排行
- 查询状态分布

## 部署方式

### 单节点部署
```bash
python3 impala_node_collector.py --host <impala_ip>
```

### 集群部署
在每个 Impala 节点上运行：
```bash
sudo ./deploy_node_collector.sh install
```

### Prometheus 配置
```yaml
scrape_configs:
  - job_name: 'impala-nodes'
    static_configs:
      - targets: ['node1:9356', 'node2:9356', 'node3:9356']
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
