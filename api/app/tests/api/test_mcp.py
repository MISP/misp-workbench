import json

import pytest
from app.auth import auth
from app.models import user as user_models
from app.settings import get_settings
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from jwt import decode as jwt_decode

MCP_URL = "/mcp"
MCP_TRANSPORT_URL = "/"


@pytest.fixture(scope="session")
def mcp_client():
    from app.main import mcp_app

    with TestClient(mcp_app) as client:
        yield client


def _parse_sse(text: str) -> list[dict]:
    """Extract JSON objects from SSE data: lines."""
    results = []
    for line in text.splitlines():
        if line.startswith("data: "):
            payload = line[len("data: "):].strip()
            if payload:
                results.append(json.loads(payload))
    return results


def _mcp_headers(auth_token=None, session_id: str = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if auth_token is not None:
        headers["Authorization"] = f"Bearer {auth_token}"
    if session_id is not None:
        headers["Mcp-Session-Id"] = session_id
    return headers


def _mcp_init(client: TestClient, auth_token=None) -> str:
    """Perform the full MCP initialization handshake and return the session ID."""
    init_body = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "0.1"},
        },
    }
    response = client.post(
        MCP_TRANSPORT_URL,
        content=json.dumps(init_body),
        headers=_mcp_headers(auth_token),
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    session_id = response.headers.get("Mcp-Session-Id", "")

    # Send the initialized notification to complete the handshake
    notif_body = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    client.post(
        MCP_TRANSPORT_URL,
        content=json.dumps(notif_body),
        headers=_mcp_headers(auth_token, session_id),
    )
    return session_id


def _mcp_request(client: TestClient, method: str, params: dict = None, auth_token=None, req_id: int = 1) -> dict:
    """Initialize an MCP session, POST a JSON-RPC 2.0 message, and return the first result."""
    session_id = _mcp_init(client, auth_token)
    body = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        body["params"] = params
    response = client.post(
        MCP_TRANSPORT_URL,
        content=json.dumps(body),
        headers=_mcp_headers(auth_token, session_id),
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    messages = _parse_sse(response.text)
    assert messages, f"No SSE data received. Response body: {response.text!r}"
    return messages[0]


# ── /mcp/config FastAPI endpoint ─────────────────────────────────────────────


class TestMcpConfigEndpoint(ApiTester):
    @pytest.mark.parametrize("scopes", [["mcp:config"]])
    def test_mcp_config_returns_structure(
        self,
        client: TestClient,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/mcp/config", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "mcpServers" in data
        assert "misp-workbench" in data["mcpServers"]

        server = data["mcpServers"]["misp-workbench"]
        assert server["type"] == "http"
        assert server["url"].endswith("/mcp")
        assert "headers" in server
        assert "Authorization" in server["headers"]
        assert server["headers"]["Authorization"].startswith("Bearer ")

    @pytest.mark.parametrize("scopes", [["mcp:config"]])
    def test_mcp_config_token_scoped_to_mcp(
        self,
        client: TestClient,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/mcp/config", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_200_OK

        bearer = response.json()["mcpServers"]["misp-workbench"]["headers"]["Authorization"]
        token = bearer.removeprefix("Bearer ")

        settings = get_settings()
        payload = jwt_decode(
            token,
            settings.OAuth2.secret_key,
            algorithms=[settings.OAuth2.algorithm],
        )
        assert "scopes" in payload
        assert all(s.startswith("mcp:") for s in payload["scopes"])

    @pytest.mark.parametrize("scopes", [[]])
    def test_mcp_config_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/mcp/config", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_mcp_config_no_token(self, client: TestClient):
        response = client.get("/mcp/config")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── MCP tools via Streamable HTTP ─────────────────────────────────────────────

class TestMcpToolsList(ApiTester):
    @pytest.mark.parametrize("scopes", [["mcp:list_tools"]])
    def test_tools_list_returns_expected_tools(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(mcp_client, "tools/list", auth_token=auth_token)
        assert "result" in msg, msg
        tools = {t["name"] for t in msg["result"]["tools"]}
        expected = {
            "search_events",
            "search_attributes",
            "get_event",
            "get_correlations",
            "detect_indicator_type",
            "get_statistics",
            "get_tags",
            "get_index_mapping",
            "search_galaxy",
            "search_taxonomy",
            "get_sightings",
            "get_sighting_activity",
            "list_hunts",
            "get_hunt_results",
            "get_hunt_history",
            "run_hunt",
            "get_event_reports",
            "search_event_reports",
            "create_event_report",
            "enrich_indicator",
            "list_modules",
            "get_notifications",
        }
        assert expected.issubset(tools)

class TestMcpToolsCall(ApiTester):
    @pytest.mark.parametrize("scopes", [["mcp:detect_indicator_type"]])
    def test_detect_indicator_type_ip(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "detect_indicator_type", "arguments": {"values": ["8.8.8.8"]}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        content = msg["result"]["content"]
        assert len(content) == 1
        result = json.loads(content[0]["text"])
        assert result[0]["value"] == "8.8.8.8"
        assert result[0]["type"] == "ip-src"

    @pytest.mark.parametrize("scopes", [["mcp:detect_indicator_type"]])
    def test_detect_indicator_type_multiple(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {
                "name": "detect_indicator_type",
                "arguments": {"values": ["evil.com", "CVE-2021-44228", "d41d8cd98f00b204e9800998ecf8427e"]},
            },
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        content = msg["result"]["content"]
        result = json.loads(content[0]["text"])
        types = {r["value"]: r["type"] for r in result}
        assert types["evil.com"] == "domain"
        assert types["CVE-2021-44228"] == "cve"
        assert types["d41d8cd98f00b204e9800998ecf8427e"] == "md5"

    @pytest.mark.parametrize("scopes", [["mcp:search_events"]])
    def test_search_events_returns_pagination_shape(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "search_events", "arguments": {"query": "*", "page": 1, "size": 5}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert "total" in result
        assert "page" in result
        assert "size" in result
        assert "results" in result
        assert result["page"] == 1
        assert result["size"] == 5

    @pytest.mark.parametrize("scopes", [["mcp:search_events"]])
    def test_search_events_size_capped_at_100(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "search_events", "arguments": {"query": "*", "size": 999}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert result["size"] == 100

    @pytest.mark.parametrize("scopes", [["mcp:search_attributes"]])
    def test_search_attributes_returns_pagination_shape(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "search_attributes", "arguments": {"query": "*"}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert "total" in result
        assert "results" in result

    @pytest.mark.parametrize("scopes", [["mcp:get_event"]])
    def test_get_event_not_found(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_event", "arguments": {"event_uuid": "00000000-0000-0000-0000-000000000000"}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert "error" in result

    @pytest.mark.parametrize("scopes", [["mcp:get_correlations"]])
    def test_get_correlations_requires_param(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_correlations", "arguments": {}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert "error" in result

    @pytest.mark.parametrize("scopes", [["mcp:get_statistics"]])
    def test_get_statistics_returns_dict(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_statistics", "arguments": {}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert isinstance(result, dict)

    @pytest.mark.parametrize("scopes", [["mcp:get_tags"]])
    def test_get_tags_returns_list(
        self,
        mcp_client: TestClient,
        auth_token: auth.Token,
        tlp_white_tag,
    ):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_tags", "arguments": {}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert isinstance(result, list)
        names = [t["name"] for t in result]
        assert "tlp:white" in names

    @pytest.mark.parametrize("scopes", [["mcp:get_tags"]])
    def test_get_tags_filter(
        self,
        mcp_client: TestClient,
        auth_token: auth.Token,
        tlp_white_tag,
    ):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_tags", "arguments": {"filter": "tlp"}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert all("tlp" in t["name"].lower() for t in result)

    @pytest.mark.parametrize("scopes", [["mcp:search_event_reports"]])
    def test_search_event_reports_returns_shape(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "search_event_reports", "arguments": {"query": "test"}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert "total" in result
        assert "results" in result

    @pytest.mark.parametrize("scopes", [["mcp:get_event_reports"]])
    def test_get_event_reports_unknown_event(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_event_reports", "arguments": {"event_uuid": "00000000-0000-0000-0000-000000000000"}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert result["total"] == 0
        assert result["results"] == []

    @pytest.mark.parametrize("scopes", [["mcp:list_modules"]])
    def test_list_modules_enabled_only(
        self,
        mcp_client: TestClient,
        auth_token: auth.Token,
        module_1_settings,
    ):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "list_modules", "arguments": {"enabled_only": True}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert isinstance(result, list)
        assert all(m["enabled"] for m in result)

    @pytest.mark.parametrize("scopes", [["mcp:list_modules"]])
    def test_list_modules_all(
        self,
        mcp_client: TestClient,
        auth_token: auth.Token,
        module_1_settings,
    ):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "list_modules", "arguments": {"enabled_only": False}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert isinstance(result, list)
        names = [m["name"] for m in result]
        assert module_1_settings.module_name in names

    @pytest.mark.parametrize("scopes", [["mcp:get_notifications"]])
    def test_get_notifications_returns_shape(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "tools/call",
            {"name": "get_notifications", "arguments": {}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        result = json.loads(msg["result"]["content"][0]["text"])
        assert "total" in result
        assert "results" in result


# ── MCP resources and prompts ─────────────────────────────────────────────────


class TestMcpResources(ApiTester):
    @pytest.mark.parametrize("scopes", [["mcp:list_resources"]])
    def test_resources_list_contains_expected(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(mcp_client, "resources/list", auth_token=auth_token)
        assert "result" in msg, msg
        uris = {r["uri"] for r in msg["result"]["resources"]}
        assert "misp://attribute-types" in uris
        assert "misp://attribute-categories" in uris
        assert "misp://threat-levels" in uris
        assert "misp://analysis-levels" in uris
        assert "misp://distribution-levels" in uris
        assert "misp://query-syntax" in uris
        assert "misp://taxonomies" in uris
        assert "misp://galaxies" in uris

    @pytest.mark.parametrize("scopes", [["mcp:list_resources"]])
    def test_read_attribute_types_resource(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "resources/read",
            {"uri": "misp://attribute-types"},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        content = msg["result"]["contents"][0]["text"]
        data = json.loads(content)
        assert "total" in data
        assert "types" in data
        assert data["total"] > 0

    @pytest.mark.parametrize("scopes", [["mcp:list_resources"]])
    def test_read_threat_levels_resource(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "resources/read",
            {"uri": "misp://threat-levels"},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        content = msg["result"]["contents"][0]["text"]
        data = json.loads(content)
        assert isinstance(data, dict)
        assert len(data) > 0


class TestMcpPrompts(ApiTester):
    @pytest.mark.parametrize("scopes", [["mcp:list_prompts"]])
    def test_prompts_list_contains_expected(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(mcp_client, "prompts/list", auth_token=auth_token)
        assert "result" in msg, msg
        names = {p["name"] for p in msg["result"]["prompts"]}
        assert "threat_report" in names
        assert "ioc_lookup" in names
        assert "threat_actor_profile" in names
        assert "country_exposure" in names
        assert "daily_summary" in names
        assert "enrich_indicator_prompt" in names

    @pytest.mark.parametrize("scopes", [["mcp:list_prompts"]])
    def test_get_ioc_lookup_prompt(self, mcp_client: TestClient, auth_token: auth.Token):
        msg = _mcp_request(
            mcp_client,
            "prompts/get",
            {"name": "ioc_lookup", "arguments": {"value": "8.8.8.8"}},
            auth_token=auth_token,
        )
        assert "result" in msg, msg
        messages = msg["result"]["messages"]
        assert len(messages) > 0
        text = messages[0]["content"]["text"]
        assert "8.8.8.8" in text
