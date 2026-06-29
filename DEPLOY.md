# Deployment

Deploy this repository as a current-quarter Feishu Project delivery intelligence pipeline.

The deployment runs:

```text
extract -> model -> current-quarter aggregate -> publish -> review
```

## Minimal Deployment

```bash
cd /opt
git clone https://github.com/kxwang5180-star/feishu-project-delivery-intelligence.git
cd feishu-project-delivery-intelligence

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/feishu-online-sheets
cp -R feishu-online-sheets ~/.codex/skills/

cd automation
cp ../server/env.example .env.local
cp config/feishu_bitable_publish.example.json config/feishu_bitable_publish.json
```

Run:

```bash
PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

Schedule:

```cron
0 8 * * 1 cd /opt/feishu-project-delivery-intelligence/automation && PYTHON_BIN=/opt/feishu-project-delivery-intelligence/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-intelligence/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```
