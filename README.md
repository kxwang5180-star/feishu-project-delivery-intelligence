# 飞书项目交付周期周度自动更新工具包

这个仓库包含两部分：

1. `feishu-online-sheets/`：Codex skill，用于把 CSV/XLSX 数据写入固定飞书电子表格或飞书多维表格 Base。
2. `automation/`：项目交付周期自动刷新任务，用于每周一统计 2025 年至上周日的季度内周度累计指标，并写入飞书 Base 的 `项目交付周期` 表。

当前目标 Base：

```text
Base app_token: NgEPbbtokaswvBstu0DcMYMlnKg
Table: 项目交付周期
table_id: tblPz1BLjGbtQymz
```

## 功能

- 从飞书项目 MCP 采集需求数据。
- 生成需求效率数据集市。
- 生成“季度 + 周次 + 需求分类”的季度内累计指标。
- 写入飞书多维表格 Base。
- 按 `季度 + 周次 + 需求分类` 幂等更新：
  - 已存在记录更新
  - 新增周次创建
  - 源数据已不存在的旧周次记录删除
  - 不做全表删除
- 跳过公式和自动字段：
  - `执行日期`
  - `研发时长/测试时长`
  - `created_at`

## 写入字段

```text
季度
周次
需求分类
需求数
平均交付周期
交付中位数
交付P90
平均研发时长
平均测试时长
```

## 数据口径

- 统计起点：`2025-01-01`
- 周度刷新：每周一统计到最近一个周日
- 周次口径：季度内第 N 个 7 天窗口
- 指标口径：
  - 平均交付周期：所有人员估分总和，来源 `field_fba983`
  - 平均研发时长：研发估分，来源 `field_db341e`
  - 平均测试时长：测试估分，来源 `field_715f2b`
- 需求分类：
  - `中小需求`：交付投入人天 <= 60
  - `大/超大需求`：交付投入人天 > 60

## 目录结构

```text
.
├── feishu-online-sheets/              # Codex skill
│   ├── SKILL.md
│   └── scripts/
│       ├── publish_sheet.py           # 写飞书电子表格
│       └── publish_bitable.py         # 写飞书 Base，多维表格
├── automation/
│   ├── scripts/
│   │   ├── collect_efficiency_enhanced.py
│   │   ├── export_efficiency_datamart.py
│   │   ├── build_quarter_week_cumulative_metrics.py
│   │   └── refresh_project_delivery_cycle_weekly.sh
│   ├── pmo_agent/                     # 飞书项目 MCP 客户端及字段解析
│   ├── config/
│   │   └── feishu_bitable_publish.example.json
│   └── docs/
│       └── project-delivery-cycle-server-deploy.md
├── examples/
├── server/
├── requirements.txt
└── DEPLOY.md
```

## 服务器部署

推荐目录：

```bash
/opt/feishu-project-delivery-cycle-updater
```

拉取代码：

```bash
cd /opt
git clone https://github.com/kxwang5180-star/Feishu-Online-Sheets-Skill.git feishu-project-delivery-cycle-updater
cd feishu-project-delivery-cycle-updater
```

创建 Python 环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

安装 Codex skill：

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/feishu-online-sheets
cp -R feishu-online-sheets ~/.codex/skills/
```

准备配置：

```bash
cd automation
cp ../server/env.example .env.local
cp config/feishu_bitable_publish.example.json config/feishu_bitable_publish.json
```

编辑 `automation/.env.local`：

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BASE_URL=https://open.feishu.cn

FEISHU_PROJECT_MCP_URL=xxx
FEISHU_PROJECT_MCP_TOKEN=xxx
MEEGO_PROJECT_KEY=信息科技部
```

`FEISHU_APP_ID` / `FEISHU_APP_SECRET` 必须使用已开通 Base 写入权限的应用。

手动执行一次：

```bash
cd /opt/feishu-project-delivery-cycle-updater/automation
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

指定截止日期：

```bash
bash scripts/refresh_project_delivery_cycle_weekly.sh 2026-06-14
```

查看日志：

```bash
tail -n 200 logs/project_delivery_cycle_weekly.log
```

## 每周自动更新

每周一 09:30 执行：

```bash
crontab -e
```

加入：

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater/automation && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## 权限要求

飞书应用至少需要：

```text
base:field:read
bitable:app
```

飞书项目 MCP 还需要可查询 `信息科技部 / 需求` 工作项。

## 注意事项

- 不要提交 `.env.local`、`FEISHU_APP_SECRET`、MCP token。
- 如果 app secret 曾经出现在聊天或日志中，建议在飞书开放平台轮换。
- 周度同步采用 upsert，不会每次全表删除。
- 若周次口径调整，脚本会删除当前源数据中不存在的旧 key。
