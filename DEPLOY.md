# Deployment

Deploy this repository as a weekly Feishu Project delivery intelligence pipeline.

The deployment is not only for writing Feishu tables. It runs the complete chain:

```text
extract -> model -> aggregate -> publish -> archive
```

## Minimal Deployment

```bash
cd /opt
git clone https://github.com/kxwang5180-star/feishu-project-delivery-cycle-updater.git
cd feishu-project-delivery-cycle-updater

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

Edit `automation/.env.local`.

Then run:

```bash
PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python \
BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py \
bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Schedule

```cron
30 9 * * 1 cd /opt/feishu-project-delivery-cycle-updater/automation && PYTHON_BIN=/opt/feishu-project-delivery-cycle-updater/.venv/bin/python BITABLE_PUBLISHER=/opt/feishu-project-delivery-cycle-updater/feishu-online-sheets/scripts/publish_bitable.py /bin/bash scripts/refresh_project_delivery_cycle_weekly.sh
```

## Read More

- [Architecture](docs/ARCHITECTURE.md)
- [Data Contract](docs/DATA_CONTRACT.md)
- [Operations](docs/OPERATIONS.md)
- [Value Model](docs/VALUE_MODEL.md)
