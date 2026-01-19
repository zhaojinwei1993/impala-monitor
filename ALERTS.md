# Impala 监控告警配置

## 告警规则说明

本配置文件包含三个核心告警规则：

### 1. 节点内存使用率告警 (ImpalaNodeMemoryUsageHigh)
- **触发条件**: 内存使用率超过80%
- **计算公式**: `(impala_memory_rss / impala_mem_tracker_process_limit) * 100 > 80`
- **持续时间**: 2分钟
- **告警级别**: warning
- **告警信息**: 主机名、IP地址、内存使用率

### 2. JVM堆内存使用率告警 (ImpalaJVMHeapUsageHigh)
- **触发条件**: JVM堆内存使用率超过80%
- **计算公式**: `(impala_jvm_heap_current_bytes / impala_jvm_heap_committed_bytes) * 100 > 80`
- **持续时间**: 2分钟
- **告警级别**: warning
- **告警信息**: 主机名、IP地址、JVM堆内存使用率

### 3. 查询执行时间告警 (ImpalaQueryExecutionTimeHigh)
- **触发条件**: 查询执行时间超过5分钟(300秒)
- **计算公式**: `impala_query_duration_seconds > 300`
- **持续时间**: 立即触发
- **告警级别**: critical
- **告警信息**: 执行人、查询ID、执行节点、执行时间、Grafana查询详情链接

## 配置使用

### 1. Prometheus配置
在Prometheus配置文件中添加告警规则：

```yaml
rule_files:
  - "prometheus-alerts.yml"
```

### 2. Alertmanager配置
配置Alertmanager来处理告警通知，例如发送到钉钉、邮件等。

### 3. 重启服务
```bash
# 重启Prometheus
sudo systemctl restart prometheus

# 重启Alertmanager
sudo systemctl restart alertmanager
```

## 告警链接说明

查询执行时间告警中包含Grafana查询详情链接：
`https://db-granfana.tigerbrokers.net/d/OlIStn7Dz/impala-queries?orgId=1&var-query_id={query_id}`

业务人员可以通过此链接查看具体的SQL查询语句和详细信息。
