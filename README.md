# Impala Monitor

Apache Impala 集群监控解决方案，提供节点级别的指标采集和 Grafana 可视化。

## 功能特性

- 🔍 **自动指标采集**：采集 Impala 节点的内存、CPU、查询等关键指标
- 📊 **Prometheus 集成**：标准 Prometheus 指标格式导出
- 📈 **Grafana 仪表板**：预配置的监控面板
- 🚀 **自动部署**：Ansible 一键部署
- 🔧 **智能配置**：自动获取网卡 IP 地址

## 项目结构

```
impala-monitor/
├── README.md                    # 项目总览
├── LICENSE                      # 许可证
├── .gitignore                   # Git 忽略文件
├── monitor/                     # 监控模块
│   ├── src/                     # 源代码
│   │   └── impala_node_collector.py
│   ├── config/                  # 配置文件
│   │   └── node_config.yaml
│   ├── scripts/                 # 工具脚本
│   │   ├── deploy_node_collector.sh
│   │   └── get_ip.py
│   ├── docs/                    # 文档
│   │   └── README_NODE_COLLECTOR.md
│   ├── requirements.txt         # Python 依赖
│   └── grafana-impala-node-dashboard.json
├── ansible/                     # Ansible 部署模块
│   ├── playbooks/              # Playbook 文件
│   │   └── deploy-impala-monitor.yml
│   ├── inventory/              # 主机清单
│   │   └── inventory.ini
│   └── scripts/                # 部署脚本
│       └── deploy.sh
└── test_data/                  # 测试数据
    ├── metrics.json
    └── query.json
```

## 快速开始

### 方式一：手动部署

```bash
# 1. 克隆仓库
git clone https://github.com/zhaojinwei1993/impala-monitor.git
cd impala-monitor

# 2. 安装依赖
pip3 install -r monitor/requirements.txt

# 3. 运行采集器
python3 monitor/src/impala_node_collector.py

# 4. 验证运行
curl http://localhost:9356/metrics
```

### 方式二：Ansible 自动部署

```bash
# 1. 配置主机清单
vim ansible/inventory/inventory.ini

# 2. 执行自动部署
cd ansible/scripts && ./deploy.sh
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
