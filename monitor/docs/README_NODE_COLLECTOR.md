# Impala Node Collector

Impala 节点指标采集器，用于采集单个 Impala 节点的监控指标并导出到 Prometheus。

## 功能特性

### 采集的指标类别

#### 1. 资源使用指标
- **内存使用**：RSS 内存、总使用内存、TCMalloc 内存使用
- **JVM 内存**：堆内存使用、非堆内存使用、GC 统计
- **Buffer Pool**：缓冲池限制、预留、已分配内存
- **线程**：运行中线程数、总创建线程数

#### 2. 查询指标
- **查询状态**：注册查询数、执行中查询数、等待查询数
- **查询统计**：总查询数、溢出查询数、过期查询数
- **查询性能**：执行时间分布、内存使用、内存估算
- **查询详情**：用户、状态、数据库、SQL 类型、资源池等

#### 3. I/O 指标
- **数据传输**：读取字节数、写入字节数
- **连接数**：HiveServer2 连接数、Beeswax 连接数

#### 4. 准入控制指标
- **资源池状态**：已接受查询数、排队查询数、运行查询数、拒绝查询数

## 采集的具体指标

### 内存指标
| 指标名称 | 类型 | 描述 | 含义 |
|---------|------|------|------|
| `impala_memory_rss_bytes` | Gauge | RSS 内存使用量 | 进程实际占用的物理内存 |
| `impala_memory_total_used_bytes` | Gauge | 总内存使用量 | TCMalloc 和 Buffer Pool 使用的总内存 |
| `impala_tcmalloc_bytes_in_use` | Gauge | TCMalloc 使用内存 | TCMalloc 分配器正在使用的内存 |
| `impala_tcmalloc_total_reserved_bytes` | Gauge | TCMalloc 预留内存 | TCMalloc 从系统预留的总内存 |
| `impala_jvm_heap_used_bytes` | Gauge | JVM 堆内存使用 | Java 堆内存当前使用量 |
| `impala_jvm_heap_committed_bytes` | Gauge | JVM 堆内存提交 | Java 堆内存已提交量 |
| `impala_jvm_non_heap_used_bytes` | Gauge | JVM 非堆内存使用 | Java 非堆内存使用量（方法区等） |

### 查询指标
| 指标名称 | 类型 | 描述 | 含义 |
|---------|------|------|------|
| `impala_queries_total` | Counter | 总查询数 | 节点处理的查询总数 |
| `impala_queries_registered` | Gauge | 注册查询数 | 当前注册的查询数量 |
| `impala_queries_executing` | Gauge | 执行中查询数 | 当前正在执行的查询数量 |
| `impala_queries_waiting` | Gauge | 等待查询数 | 等待关闭的查询数量 |
| `impala_query_duration_seconds` | Histogram | 查询执行时间 | 查询执行时间分布 |
| `impala_query_memory_usage_bytes` | Gauge | 查询内存使用 | 单个查询的内存使用量 |
| `impala_query_memory_estimate_bytes` | Gauge | 查询内存估算 | 单个查询的内存估算量 |

### 系统指标
| 指标名称 | 类型 | 描述 | 含义 |
|---------|------|------|------|
| `impala_threads_running` | Gauge | 运行线程数 | 当前运行的线程数量 |
| `impala_connections_hiveserver2` | Gauge | HiveServer2 连接数 | 活跃的 HiveServer2 连接数 |
| `impala_bytes_read_total` | Counter | 读取字节总数 | 从数据源读取的总字节数 |
| `impala_bytes_written_total` | Counter | 写入字节总数 | 写入磁盘的总字节数 |

### 准入控制指标
| 指标名称 | 类型 | 描述 | 含义 |
|---------|------|------|------|
| `impala_admission_admitted_total` | Counter | 已接受查询总数 | 资源池接受的查询总数 |
| `impala_admission_queued` | Gauge | 排队查询数 | 资源池中排队的查询数 |
| `impala_admission_running` | Gauge | 运行查询数 | 资源池中运行的查询数 |
| `impala_admission_rejected_total` | Counter | 拒绝查询总数 | 资源池拒绝的查询总数 |

## 安装部署

### 1. 环境要求
- Python 3.6+
- 可访问 Impala 节点的 Web UI（默认端口 25000）
- 系统管理员权限（用于创建系统服务）

### 2. 安装依赖
```bash
pip3 install -r requirements.txt
```

### 3. 配置文件
编辑 `node_config.yaml`：
```yaml
# Impala 节点配置
# 如果不指定 impala_host，程序会自动获取 eth0 网卡的 IP 地址
# impala_host: "192.168.1.100"  # 可以手动指定 IP 地址
impala_port: 25000        # Impala Web UI 端口

# Prometheus 指标服务端口
metrics_port: 9356        # 指标导出端口

# 采集间隔（秒）
collect_interval: 30      # 采集频率

# 超时设置
timeout: 10               # HTTP 请求超时
```

**IP 地址自动获取**：
- 程序会自动尝试获取 eth0 网卡的 IP 地址
- 如果 eth0 不存在，会使用其他方法获取本机 IP
- 也可以在配置文件中手动指定 `impala_host`

**测试 IP 获取**：
```bash
python3 get_ip.py
```

### 4. 部署方式

#### 方式一：自动部署（推荐）
```bash
sudo ./deploy_node_collector.sh install
```

#### 方式二：手动运行
```bash
python3 impala_node_collector.py --config node_config.yaml
```

#### 方式三：指定参数运行
```bash
python3 impala_node_collector.py \
  --host 192.168.1.100 \
  --port 25000 \
  --metrics-port 9356
```

## 服务管理

### 启动/停止服务
```bash
# 启动服务
sudo systemctl start impala-node-collector

# 停止服务
sudo systemctl stop impala-node-collector

# 重启服务
sudo systemctl restart impala-node-collector

# 查看状态
sudo systemctl status impala-node-collector

# 查看日志
sudo journalctl -u impala-node-collector -f
```

### 开机自启
```bash
sudo systemctl enable impala-node-collector
```

## Prometheus 配置

在 Prometheus 配置文件中添加采集目标：

```yaml
scrape_configs:
  - job_name: 'impala-nodes'
    static_configs:
      - targets: 
        - 'node1:9356'
        - 'node2:9356'
        - 'node3:9356'
    scrape_interval: 30s
    metrics_path: /metrics
```

## Grafana 仪表板

### 导入仪表板
1. 登录 Grafana
2. 点击 "+" -> "Import"
3. 上传 `grafana-impala-node-dashboard.json` 文件
4. 选择 Prometheus 数据源
5. 点击 "Import"

### 仪表板功能
- **内存使用监控**：RSS、TCMalloc、JVM 内存使用趋势
- **查询状态监控**：注册、执行、等待查询数量
- **系统资源监控**：线程数、连接数变化
- **活跃查询表格**：显示当前运行查询的详细信息
- **查询状态分布**：按状态统计查询数量
- **I/O 速率监控**：读写速率趋势
- **查询性能分析**：执行时间百分位数
- **准入控制监控**：资源池状态

### 重点关注指标

#### 1. 资源使用情况
- **内存使用率**：`impala_memory_rss_bytes` / 系统总内存
- **JVM 堆使用率**：`impala_jvm_heap_used_bytes` / `impala_jvm_heap_max_bytes`
- **Buffer Pool 使用率**：`impala_buffer_pool_system_allocated_bytes` / `impala_buffer_pool_limit_bytes`

#### 2. 查询性能
- **查询执行时间**：`impala_query_duration_seconds` 的 P95、P99
- **查询内存使用**：`impala_query_memory_usage_bytes` 按用户、状态分组
- **查询排队情况**：`impala_admission_queued` 按资源池分组

#### 3. 系统健康
- **连接数**：`impala_connections_hiveserver2` 监控客户端连接
- **线程数**：`impala_threads_running` 监控系统负载
- **I/O 吞吐**：`rate(impala_bytes_read_total[5m])` 监控数据处理量

## 故障排查

### 1. 服务无法启动
```bash
# 检查服务状态
sudo systemctl status impala-node-collector

# 查看详细日志
sudo journalctl -u impala-node-collector -n 50

# 检查配置文件
cat /etc/impala-monitor/node_config.yaml

# 手动测试
sudo -u impala-monitor python3 /opt/impala-monitor/impala_node_collector.py --config /etc/impala-monitor/node_config.yaml
```

### 2. 无法连接 Impala 节点
```bash
# 测试网络连通性
curl http://impala-host:25000/metrics?json

# 检查防火墙
sudo firewall-cmd --list-ports
```

### 3. 指标数据异常
```bash
# 检查指标端点
curl http://localhost:9356/metrics

# 验证 Prometheus 采集
curl http://prometheus:9090/api/v1/query?query=impala_memory_rss_bytes
```

## 卸载

```bash
sudo ./deploy_node_collector.sh uninstall
```

## 扩展开发

### 添加自定义指标
1. 在 `_init_metrics()` 方法中定义新指标
2. 在 `_process_single_metric()` 方法中添加处理逻辑
3. 更新 Grafana 仪表板

### 支持新的数据源
1. 实现新的 `_fetch_*()` 方法
2. 添加对应的 `_process_*()` 处理方法
3. 在 `collect_metrics()` 中调用

## 许可证

本项目采用 MIT 许可证。
