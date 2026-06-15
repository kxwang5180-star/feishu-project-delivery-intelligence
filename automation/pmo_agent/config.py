from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .efficiency_fields import EfficiencyFieldConfig

ROOT = Path(__file__).resolve().parent.parent


def load_env_files(root: Path = ROOT) -> None:
    """Load local env files without overriding existing process values."""
    for name in (".env.local", ".env"):
        path = root / name
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    app_version: str
    timezone: str
    pmo_agent_token: str
    openai_model: str
    database_path: Path
    report_dir: Path
    project_key: str
    project_name: str
    project_simple_name: str
    work_item_type: str
    work_item_type_key: str
    work_item_url_template: str
    meego_plugin_id: str
    meego_plugin_secret: str
    meego_base_url: str
    meego_mql_endpoint: Optional[str]
    meego_user_key: str
    feishu_project_mcp_url: Optional[str]
    feishu_project_mcp_authorization: Optional[str]
    feishu_project_mcp_token: Optional[str]
    feishu_project_mcp_mql_tool: Optional[str]
    feishu_doc_script_path: Optional[Path]
    efficiency_fields: EfficiencyFieldConfig = field(default_factory=EfficiencyFieldConfig.from_env)

    @classmethod
    def from_env(cls, root: Path = ROOT) -> "Settings":
        load_env_files(root)
        script_path = os.environ.get(
            "FEISHU_DOC_SCRIPT_PATH",
            "/Users/kk/.codex/skills/feishu-online-docs/scripts/create_feishu_doc.py",
        )
        return cls(
            app_version="0.1.0",
            timezone=os.environ.get("PMO_TIMEZONE", "Asia/Shanghai"),
            pmo_agent_token=os.environ.get("PMO_AGENT_TOKEN", ""),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-5.5"),
            database_path=Path(os.environ.get("PMO_AGENT_DB", str(root / "data" / "pmo_agent.sqlite3"))),
            report_dir=Path(os.environ.get("PMO_REPORT_DIR", str(root / "reports"))),
            project_key=os.environ.get("MEEGO_PROJECT_KEY", "62a43e1881329ed76a597141"),
            project_name=os.environ.get("MEEGO_PROJECT_NAME", "信息科技部"),
            project_simple_name=os.environ.get("MEEGO_PROJECT_SIMPLE_NAME", "hdltech"),
            work_item_type=os.environ.get("MEEGO_WORK_ITEM_TYPE", "需求"),
            work_item_type_key=os.environ.get("MEEGO_WORK_ITEM_TYPE_KEY", "story"),
            work_item_url_template=os.environ.get(
                "FEISHU_PROJECT_WORK_ITEM_URL_TEMPLATE",
                "https://project.feishu.cn/{project_simple_name}/{work_item_type_key}/detail/{work_item_id}",
            ),
            meego_plugin_id=os.environ.get("MEEGO_PLUGIN_ID", ""),
            meego_plugin_secret=os.environ.get("MEEGO_PLUGIN_SECRET", ""),
            meego_base_url=os.environ.get("MEEGO_BASE_URL", "https://project.feishu.cn").rstrip("/"),
            meego_mql_endpoint=os.environ.get("MEEGO_MQL_ENDPOINT") or None,
            meego_user_key=os.environ.get("MEEGO_USER_KEY", ""),
            feishu_project_mcp_url=os.environ.get("FEISHU_PROJECT_MCP_URL") or os.environ.get("FEISHU_MCP_URL") or None,
            feishu_project_mcp_authorization=os.environ.get("FEISHU_PROJECT_MCP_AUTHORIZATION")
            or os.environ.get("FEISHU_MCP_AUTHORIZATION")
            or None,
            feishu_project_mcp_token=os.environ.get("FEISHU_PROJECT_MCP_TOKEN")
            or os.environ.get("FEISHU_MCP_TOKEN")
            or None,
            feishu_project_mcp_mql_tool=os.environ.get("FEISHU_PROJECT_MCP_MQL_TOOL") or None,
            feishu_doc_script_path=Path(script_path) if script_path else None,
            efficiency_fields=EfficiencyFieldConfig.from_env(),
        )
