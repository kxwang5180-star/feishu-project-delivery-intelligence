# 部署说明

完整说明见：

```text
README.md
automation/docs/project-delivery-cycle-server-deploy.md
```

最短路径：

```bash
cd /opt
git clone https://github.com/kxwang5180-star/Feishu-Online-Sheets-Skill.git feishu-project-delivery-cycle-updater
cd feishu-project-delivery-cycle-updater

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p ~/.codex/skills
cp -R feishu-online-sheets ~/.codex/skills/

cd automation
cp ../server/env.example .env.local
cp config/feishu_bitable_publish.example.json config/feishu_bitable_publish.json
```

编辑 `automation/.env.local` 后执行：

```bash
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```
