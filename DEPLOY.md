# Impala Monitor 部署指南

## 项目结构

```
impala-monitor/
├── monitor/                     # 监控模块
│   ├── src/                     # 源代码
│   │   ├── impala_monitor.py    # 主监控程序
│   │   └── impala_exporter.py   # 指标导出器
│   ├── config/                  # 配置文件
│   │   └── node_config.yaml     # 节点配置
│   ├── scripts/                 # 部署脚本
│   │   └── deploy_node_collector.sh
│   ├── requirements.txt         # Python 依赖
│   └── grafana-impala-dashboard.json
├── ansible/                     # Ansible 批量部署
│   ├── playbooks/              # Playbook 文件
│   ├── templates/              # 服务模板
│   ├── inventory/              # 主机清单
│   └── scripts/                # 部署脚本
└── README.md                   # 项目说明
```

## 部署方式

### 方式一：单节点手动部署

1. **安装依赖**
```bash
cd impala-monitor/monitor
pip3 install -r requirements.txt
```

2. **配置文件**
```bash
# 编辑配置文件
vim config/node_config.yaml
```

3. **直接运行**
```bash
python3 src/impala_monitor.py --host <impala_host>
```

4. **验证运行**
```bash
curl http://localhost:9356/metrics
```

### 方式二：单节点服务部署

1. **使用部署脚本**
```bash
cd monitor/scripts
sudo ./deploy_node_collector.sh install
```

2. **检查服务状态**
```bash
sudo systemctl status impala-monitor
```

3. **查看日志**
```bash
sudo journalctl -u impala-monitor -f
```

### 方式三：Ansible 批量部署

1. **配置主机清单**
```bash
vim ansible/inventory/inventory.ini
```

2. **执行批量部署**
```bash
cd ansible/scripts
./deploy.sh
```

## 监控指标

### 核心指标
- **内存指标**：进程限制、RSS、总使用量
- **JVM 指标**：堆内存、非堆内存、GC 时间
- **查询指标**：执行中、等待中、总数量
- **具体查询**：内存使用、执行时间、用户信息

### 标签支持
所有指标都包含：
- `host_ip`: 主机 IP 地址
- `hostname`: 主机名
- `query_id`: 查询 ID（查询级别指标）
- `effective_user`: 执行用户（查询级别指标）
- `state`: 查询状态（查询级别指标）

## Prometheus 配置

```yaml
scrape_configs:
  - job_name: 'impala-nodes'
    static_configs:
      - targets: ['node1:9356', 'node2:9356', 'node3:9356']
    scrape_interval: 30s
```

## Grafana 仪表板

导入 `monitor/grafana-impala-dashboard.json` 到 Grafana。

支持功能：
- 主机过滤器
- 按主机分组的图表
- 查询详情表格
- 内存和 JVM 监控

## 卸载

### 单节点卸载
```bash
cd monitor/scripts
sudo ./deploy_node_collector.sh uninstall
```

### 批量卸载
```bash
cd ansible/scripts
./uninstall.sh
```

## 故障排查

1. **检查连接**
```bash
curl http://<impala_host>:25000/metrics?json
```

2. **查看日志**
```bash
sudo journalctl -u impala-monitor -n 50
```

3. **测试指标**
```bash
curl http://localhost:9356/metrics | grep impala
```
