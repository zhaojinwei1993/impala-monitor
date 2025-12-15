# Impala Monitor

Apache Impala 集群监控解决方案，提供节点级别的指标采集和 Grafana 可视化。

## 功能特性

- 🔍 **自动指标采集**：采集 Impala 节点的内存、CPU、查询等关键指标
- 📊 **Prometheus 集成**：标准 Prometheus 指标格式导出
- 📈 **Grafana 仪表板**：预配置的监控面板
- 🚀 **自动部署**：Ansible 一键部署
- 🔧 **智能配置**：自动获取网卡 IP 地址
- 🏷️ **主机标签**：支持主机IP和主机名标签，便于多节点管理

## 项目结构

```
impala-monitor/
├── README.md                    # 项目总览
├── LICENSE                      # 许可证
├── .gitignore                   # Git 忽略文件
├── monitor/                     # 监控模块
│   ├── src/                     # 源代码
│   │   ├── impala_monitor.py    # 主监控程序
│   │   └── impala_exporter.py   # 指标导出器
│   ├── config/                  # 配置文件
│   │   └── node_config.yaml
│   ├── scripts/                 # 工具脚本
│   │   ├── deploy_node_collector.sh
│   │   └── test_monitor.py
│   ├── docs/                    # 文档
│   │   └── README_NODE_COLLECTOR.md
│   ├── requirements.txt         # Python 依赖
│   └── grafana-impala-dashboard.json
├── ansible/                     # Ansible 部署模块
│   ├── playbooks/              # Playbook 文件
│   │   ├── deploy-impala-monitor.yml
│   │   └── uninstall-impala-monitor.yml
│   ├── templates/              # 模板文件
│   │   └── impala-monitor.service.j2
│   ├── inventory/              # 主机清单
│   │   └── inventory.ini
│   ├── scripts/                # 部署脚本
│   │   ├── deploy.sh
│   │   ├── uninstall.sh
│   │   └── quick-uninstall.sh
│   └── docs/                   # 部署文档
│       └── UNINSTALL.md
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
python3 monitor/src/impala_monitor.py

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

### 方式三：单节点部署

```bash
# 1. 使用部署脚本
cd monitor/scripts
sudo ./deploy_node_collector.sh install

# 2. 测试部署
python3 test_monitor.py --host <impala_host>
```

## 卸载

### 单节点卸载

```bash
# 卸载服务
cd monitor/scripts
sudo ./deploy_node_collector.sh uninstall

# 手动卸载
sudo systemctl stop impala-monitor
sudo systemctl disable impala-monitor
sudo rm -rf /opt/impala-monitor
```

### 多节点卸载

```bash
# 1. 配置要卸载的节点清单
vim ansible/inventory/inventory.ini

# 2. 执行批量卸载
cd ansible/scripts
./uninstall.sh

# 3. 验证卸载结果
./uninstall.sh --verify
```

卸载选项：
- `--remove-packages`: 同时删除 Python 依赖包
- `--limit node1,node2`: 只卸载指定节点
- `--dry-run`: 预览模式，不实际执行
- `--verify`: 验证卸载是否完成

## 监控指标

### 核心指标（带主机标签）
- **内存使用**：RSS、TCMalloc、JVM 堆内存
- **查询状态**：执行中、等待、排队查询数量（瞬时值）
- **查询性能**：执行时间、内存使用分布
- **系统资源**：线程数、连接数、I/O 吞吐

### 主机标签支持
所有指标都包含以下标签：
- `host_ip`: 主机 IP 地址
- `hostname`: 主机名

这样在 Grafana 中可以：
- 按主机过滤查看单独的主机信息
- 对比不同主机的指标
- 创建主机级别的告警

### 查询详情
- 实时查询列表（用户、SQL、内存使用、运行时间）
- 资源占用排行
- 查询状态分布（当前瞬时值，非累计值）

## 部署方式

### 单节点部署
```bash
python3 impala_monitor.py --host <impala_ip>
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

## Grafana 仪表板

新的 Grafana 仪表板支持：
- 主机过滤器：可以选择特定主机或查看所有主机
- 主机 IP 过滤器：可以按 IP 地址过滤
- 按主机分组的图表：每个图表都显示主机信息
- 主机信息表：显示所有主机的详细信息

导入 `monitor/grafana-impala-dashboard.json` 到 Grafana。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
