# United Blacklist Manager

> 开源·实用·高效·福瑞

基于OneBot协议的分布式群组安全管理机器人，实现跨群黑名单实时同步与自动化管控。

## 主要功能

- 🛡️ **实时黑名单同步**
  - 定时从中央服务器获取最新黑名单（6小时/次）
  - 启动时强制同步校验机制
- 🤖 **自动化成员管理**
  - 新成员黑名单即时检测与拦截
  - 支持20种随机化人性化提醒模板
  - 自然行为模拟（消息延迟1-3秒，操作间隔0.5-1秒）
- 🔍 **安全扫描系统**
  - 启动时全量成员扫描
  - 历史黑名单成员自动清理
- 📊 **日志监控**
  - 多层级日志记录（INFO/WARNING/ERROR）
  - 同时支持文件日志和控制台输出

## 快速开始

### 前置要求
- Python 3.12
- OneBot v11兼容的QQ机器人框架
- QQ群组的管理员权限

### 安装依赖

```bash
pip install -r requirements.txt
```

### 设置作用域
1. 在`group.txt`中添加需要管理的群号，每行一个，UTF-8编码。
2. 在`onebot_client.py`中设置黑名单拉取地址，每行一个，UTF-8编码。

### 启动机器人

```bash
python onebot_client.py
```
## 特别鸣谢

- LLQQNT
- OneBot
- Trae IDE
- DeepSeek