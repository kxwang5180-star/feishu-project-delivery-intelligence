# 项目交付周期周度自动更新部署说明

## 目标

每周一刷新飞书 Base `项目交付周期` 表，统计范围为 2025-01-01 至上周日。每条记录代表某季度内某周截至日的累计指标，并按需求分类拆分为：

- 中小需求
- 大/超大需求

## 更新链路

1. 从飞书项目采集 2025-01-01 至上周日的需求数据。
2. 生成本地数据集市。
3. 生成 `quarter_week_cumulative_metrics.csv`。
4. 按 `季度 + 周次 + 需求分类` 匹配飞书 Base 现有记录。
5. 已存在的记录更新，新增周次才创建；当前源数据里已不存在的旧周次键会被删除，避免每周全表删除。

## 服务器目录

推荐部署到：

```bash
/opt/feishu-project-delivery-cycle-updater
```

## 环境变量

服务器需要在项目根目录放 `.env.local`，至少包含：

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BASE_URL=https://open.feishu.cn

FEISHU_PROJECT_MCP_URL=xxx
FEISHU_PROJECT_MCP_TOKEN=xxx
MEEGO_PROJECT_KEY=信息科技部
```

`FEISHU_APP_ID` / `FEISHU_APP_SECRET` 必须使用已开通 Base 写入权限的应用。当前验证通过的是用户提供的新应用，而不是旧 `.env.local` 里的应用。

不要把 `.env.local` 提交到 Git。

## Python 依赖

导出 Excel 数据集市需要 `openpyxl`：

```bash
python3 -m pip install openpyxl
```

如果服务器使用虚拟环境，可以设置：

```bash
export PYTHON_BIN=/path/to/venv/bin/python
```

飞书 Base 发布脚本默认位置：

```bash
export BITABLE_PUBLISHER=$HOME/.codex/skills/feishu-online-sheets/scripts/publish_bitable.py
```

## 手动执行

默认统计到最近一个周日，适合周一运行：

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

指定统计截止日：

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-14
```

## Cron

每周一 09:30 执行：

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater/automation && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## 日志

```bash
tail -n 200 logs/project_delivery_cycle_weekly.log
```

## 飞书 Base 写入配置

配置文件：

```text
config/feishu_bitable_publish.json
```

当前目标：

```text
app_token = NgEPbbtokaswvBstu0DcMYMlnKg
table_id  = tblPz1BLjGbtQymz
```

幂等键：

```text
季度 + 周次 + 需求分类
```

跳过字段：

```text
执行日期
研发时长/测试时长
created_at
```

这些字段由飞书公式或自动时间处理。
