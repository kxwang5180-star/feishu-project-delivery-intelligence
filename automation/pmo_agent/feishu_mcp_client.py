from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from . import mql
from .config import Settings
from .meego_client import MeegoClientError, extract_records
from .metrics import moql_field_list_to_record, normalize_record
from .models import DemandItem, InspectionDataset
from .periods import InspectionPeriod


class FeishuMCPClientError(MeegoClientError):
    pass


@dataclass(frozen=True)
class MCPHTTPResponse:
    status_code: int
    headers: Mapping[str, str]
    text: str


class FeishuMCPClient:
    """Read-only Feishu Project MCP client using MCP Streamable HTTP.

    The official Lark/Feishu MCP server exposes platform APIs as MCP tools.
    This client discovers the MQL search tool and calls it with the same
    read-only queries used by the OpenAPI fallback client.
    """

    def __init__(self, settings: Settings):
        if not settings.feishu_project_mcp_url:
            raise FeishuMCPClientError("Missing FEISHU_PROJECT_MCP_URL")
        self.settings = settings
        self.url = settings.feishu_project_mcp_url
        self.authorization = settings.feishu_project_mcp_authorization
        self.mcp_token = settings.feishu_project_mcp_token
        self.mql_tool_name = settings.feishu_project_mcp_mql_tool
        self._session_id: Optional[str] = None
        self._initialized = False
        self._request_id = 0

    async def collect_dataset(self, period: InspectionPeriod) -> InspectionDataset:
        project_name = self.settings.project_name
        work_item_type = self.settings.work_item_type
        return InspectionDataset(
            period=period,
            updated=await self.query_mql(mql.updated_demands(project_name, work_item_type, period)),
            created=await self.query_mql(mql.created_demands(project_name, work_item_type, period)),
            completed=await self.query_mql(mql.completed_demands(project_name, work_item_type, period)),
            backlog=await self.query_mql(mql.active_backlog(project_name, work_item_type)),
            high_priority=await self.query_mql(mql.high_priority(project_name, work_item_type)),
            risk_candidates=await self.query_mql(mql.risk_candidates(project_name, work_item_type, period)),
            yearly_completed=await self.collect_efficiency_completed(period),
        )

    async def collect_efficiency_completed(self, period: InspectionPeriod) -> List[DemandItem]:
        project_name = self.settings.project_name
        work_item_type = self.settings.work_item_type
        items: List[DemandItem] = []
        for start, end in mql.daily_ranges(period.start, period.end):
            items.extend(
                await self.query_mql(
                    mql.completed_efficiency_demands(project_name, work_item_type, start, end, self.settings.efficiency_fields)
                )
            )
        return items

    async def query_mql(self, query: str) -> List[DemandItem]:
        records = await self.query_mql_records(query)
        return [normalize_record(record, efficiency_fields=self.settings.efficiency_fields) for record in records]

    async def query_mql_records(self, query: str) -> List[Dict[str, Any]]:
        await self.initialize()
        tool_name = await self.resolve_mql_tool()
        result = await self.call_tool(
            tool_name,
            {
                "project_key": self.settings.project_key,
                "mql": query,
            },
        )
        payload = mcp_tool_payload(result)
        return extract_records(payload)

    async def probe_efficiency_fields(self, period: InspectionPeriod) -> List[Dict[str, Any]]:
        project_name = self.settings.project_name
        work_item_type = self.settings.work_item_type
        fields = self.settings.efficiency_fields.select_fields()
        results: List[Dict[str, Any]] = []
        for field in fields:
            query = mql.efficiency_field_probe_query(project_name, work_item_type, period.start, period.end, field)
            try:
                records = await self.query_mql_records(query)
                values = non_empty_field_values(records, field)
                results.append(
                    {
                        "field": field,
                        "status": "ok",
                        "record_count": len(records),
                        "non_empty_count": len(values),
                        "sample_values": values[:5],
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "field": field,
                        "status": "error",
                        "record_count": 0,
                        "non_empty_count": 0,
                        "sample_values": [],
                        "error": str(exc),
                    }
                )
        return results

    async def initialize(self) -> None:
        if self._initialized:
            return
        response = await self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "feishu-pmo-agent", "version": self.settings.app_version},
            },
        )
        if "result" not in response:
            raise FeishuMCPClientError(f"MCP initialize failed: {response}")
        await self.rpc("notifications/initialized", {}, notification=True)
        self._initialized = True

    async def list_tools(self) -> List[Dict[str, Any]]:
        await self.initialize()
        response = await self.rpc("tools/list", {})
        tools = response.get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            raise FeishuMCPClientError(f"MCP tools/list returned unexpected payload: {response}")
        return [tool for tool in tools if isinstance(tool, dict)]

    async def resolve_mql_tool(self) -> str:
        if self.mql_tool_name:
            return self.mql_tool_name
        tools = await self.list_tools()
        names = [str(tool.get("name", "")) for tool in tools if tool.get("name")]
        for name in names:
            if normalize_tool_name(name) == "search_by_mql":
                self.mql_tool_name = name
                return name
        for name in names:
            lowered = normalize_tool_name(name)
            if "search_by_mql" in lowered or lowered.endswith(".mql") or "mql" in lowered:
                self.mql_tool_name = name
                return name
        sample = ", ".join(names[:20])
        raise FeishuMCPClientError(
            "Could not find a Feishu Project MQL MCP tool. "
            "Set FEISHU_PROJECT_MCP_MQL_TOOL to the exact tool name. "
            f"Available tools: {sample or 'none'}"
        )

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in response:
            raise FeishuMCPClientError(f"MCP tool call failed: {response['error']}")
        return response.get("result", {})

    async def rpc(self, method: str, params: Dict[str, Any], *, notification: bool = False) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.authorization:
            headers["Authorization"] = self.authorization if " " in self.authorization else f"Bearer {self.authorization}"
        if self.mcp_token:
            headers["X-Mcp-Token"] = self.mcp_token
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            self._request_id += 1
            payload["id"] = self._request_id

        response = await post_json(self.url, payload, headers, timeout=45)
        session_id = response.headers.get("mcp-session-id") or response.headers.get("Mcp-Session-Id")
        if session_id:
            self._session_id = session_id
        if notification and response.status_code in (200, 202, 204):
            return {}
        if response.status_code >= 400:
            raise FeishuMCPClientError(f"MCP HTTP {response.status_code}: {response.text[:500]}")
        return parse_mcp_http_response(response.headers.get("content-type", ""), response.text)


async def post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], *, timeout: int) -> MCPHTTPResponse:
    try:
        import httpx
    except ImportError:
        import asyncio

        return await asyncio.to_thread(post_json_with_urllib, url, payload, headers, timeout=timeout)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
    return MCPHTTPResponse(status_code=response.status_code, headers=response.headers, text=response.text)


def post_json_with_urllib(url: str, payload: Dict[str, Any], headers: Dict[str, str], *, timeout: int) -> MCPHTTPResponse:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            status = response.status if hasattr(response, "status") else response.getcode()
            return MCPHTTPResponse(
                status_code=int(status),
                headers=dict(response.headers.items()),
                text=body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return MCPHTTPResponse(status_code=int(exc.code), headers=dict(exc.headers.items()), text=body)


def normalize_tool_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def parse_mcp_http_response(content_type: str, body: str) -> Dict[str, Any]:
    if "text/event-stream" in content_type:
        data_lines: List[str] = []
        for line in body.splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    data_lines.append(data)
        for data in reversed(data_lines):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise FeishuMCPClientError("MCP SSE response did not contain JSON data")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise FeishuMCPClientError(f"MCP response was not JSON: {body[:200]}") from exc
    if not isinstance(parsed, dict):
        raise FeishuMCPClientError(f"MCP response was not an object: {parsed}")
    return parsed


def mcp_tool_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    if isinstance(structured, list):
        return {"items": structured}

    content = result.get("content", [])
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                return json_text_payload(text)
    if isinstance(result, dict):
        return result
    return {}


def json_text_payload(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {"text": text}
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {"items": parsed}
    return {"value": parsed}


def non_empty_field_values(records: List[Dict[str, Any]], field: str) -> List[str]:
    values: List[str] = []
    seen = set()
    for record in records:
        fields = moql_field_list_to_record(record["moql_field_list"]) if isinstance(record.get("moql_field_list"), list) else record
        if isinstance(fields.get("fields"), dict):
            fields = fields["fields"]
        value = fields.get(field)
        label = probe_value_label(value)
        if not label or label in seen:
            continue
        seen.add(label)
        values.append(label)
    return values


def probe_value_label(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return "、".join(label for label in (probe_value_label(item) for item in value) if label)
    if isinstance(value, dict):
        for key in ("label", "option_name", "name", "cn_name", "name_cn", "value", "id"):
            if value.get(key) not in (None, ""):
                return str(value[key])
        return ""
    return str(value)
