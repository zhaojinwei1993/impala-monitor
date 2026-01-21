# Impala Query Killer 快速参考

## 一分钟快速部署

### 批量部署（推荐）
```bash
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
cd ansible/scripts && ./deploy_query_killer.sh
```

### 单节点部署
```bash
sudo mkdir -p /opt/impala-monitor/config
sudo cp monitor/config/query_killer.conf /opt/impala-monitor/config/
sudo vim /opt/impala-monitor/config/query_killer.conf  # 填写 IMPALA_HOST 和 FEISHU_WEBHOOK
cd monitor/scripts && sudo ./deploy_query_killer.sh install
```

## 常用命令

```bash
# 查看状态
sudo systemctl status impala-query-killer

# 重启服务
sudo systemctl restart impala-query-killer

# 查看日志
sudo tail -f /opt/impala-monitor/logs/query_killer.log

# 修改配置
sudo vim /opt/impala-monitor/config/query_killer.conf
sudo systemctl restart impala-query-killer

# 卸载
cd monitor/scripts && sudo ./deploy_query_killer.sh uninstall
```

## 架构图

```
每个 Impala 节点
├── Impalad (:25000)
└── Query Killer
    ├── 每 60 秒检查一次
    ├── 监控本节点查询
    ├── Kill 超标查询
    └── 发送飞书通知
```

## 默认阈值

- 运行时间：600 秒（10 分钟）
- 内存使用：1024 GB（1 TB）
- 检查间隔：60 秒

## 详细文档

查看 [QUERY_KILLER.md](QUERY_KILLER.md) 获取完整文档。
