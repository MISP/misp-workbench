"""Vendor API sinks (Sentinel, Defender, Elastic) against recorded responses.

A local HTTP server stands in for Microsoft Entra ID and each API: it answers
with the recorded responses in ``tests/fixtures/vendor_sinks`` and keeps every
request, so the tests check what is sent as much as how answers are read.
"""

import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from app.repositories import sinks as sinks_repository
from app.schemas import sink as sink_schemas
from app.services.sinks import formatters, vendors
from app.services.sinks.transports import SinkDeliveryError, open_transport

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures", "vendor_sinks")
NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
WORKSPACE = "00000000-0000-4000-8000-0000000000aa"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.recorded-token.signature"


def fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


class Api:
    """Answers each path with its queued responses, the last one repeating."""

    def __init__(self):
        self.routes: dict = {}
        self.requests: list = []

    def on(self, method, path, *responses):
        self.routes[(method, path)] = list(responses)

    def calls(self, method=None, path=None):
        return [
            r
            for r in self.requests
            if (method is None or r["method"] == method)
            and (path is None or r["path"] == path)
        ]


@pytest.fixture
def api():
    state = Api()

    class Handler(BaseHTTPRequestHandler):
        def _answer(self):
            url = urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8") if length else ""
            state.requests.append(
                {
                    "method": self.command,
                    "path": url.path,
                    "query": parse_qs(url.query),
                    "headers": dict(self.headers),
                    "body": body,
                }
            )
            queue = state.routes.get((self.command, url.path)) or [(404, "", {})]
            status, payload, headers = queue.pop(0) if len(queue) > 1 else queue[0]
            data = payload.encode("utf-8")
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_HEAD = _answer

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    ).start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    yield state
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    waits = []
    monkeypatch.setattr(vendors.time, "sleep", waits.append)
    return waits


def record(type_, value, **extra):
    attribute = {
        "uuid": "a1",
        "type": type_,
        "value": value,
        "to_ids": True,
        "timestamp": 1790000000,
        "tags": [{"name": "tlp:amber"}],
    }
    event = {"uuid": "e1", "info": "C2 report", "threat_level": 1, "tags": []}
    return {**formatters.build_record(attribute, event), **extra}


def removal(type_, value):
    return formatters.removal_record(
        {"uuid": "i1", "type": type_, "value": value, "reason": "max_age_days"}
    )


def entra(api, **config):
    api.on(
        "POST",
        "/tenant.example/oauth2/v2.0/token",
        (200, fixture("entra_token.json"), {}),
    )
    return {
        "tenant_id": "tenant.example",
        "client_id": "app-id",
        "client_secret": "app-secret",
        "login_url": api.url,
        **config,
    }


def sentinel(api, **config):
    cfg = sink_schemas.validate_config(
        "sentinel",
        entra(api, workspace_id=WORKSPACE, api_url=api.url, **config),
    )
    return vendors.SentinelTransport(cfg, now=lambda: NOW)


def defender(api, **config):
    cfg = sink_schemas.validate_config(
        "defender", entra(api, api_url=api.url, **config)
    )
    return vendors.DefenderTransport(cfg, now=lambda: NOW)


UPLOAD = f"/workspaces/{WORKSPACE}/threat-intelligence-stix-objects:upload"


class TestRecords:
    def test_observables(self):
        assert vendors.observables(
            record("domain|ip", "Evil.example|185.220.101.42")
        ) == [
            ("domain", "evil.example"),
            ("ipv4", "185.220.101.42"),
        ]
        assert vendors.observables(record("filename|sha256", "a.exe|" + "A" * 64)) == [
            ("filename", "a.exe"),
            ("sha256", "a" * 64),
        ]

    @pytest.mark.parametrize(
        "type_,value",
        [
            ("ip-dst", "0.0.0.0/0"),
            ("ip-dst", "127.0.0.1"),
            ("ip-dst", "::ffff:0:0/96"),
            ("domain", "co.uk"),
            ("md5", "not-a-hash"),
            ("url", "http://a b"),
            ("text", "anything"),
        ],
    )
    def test_what_no_vendor_gets(self, type_, value):
        assert vendors.observables(record(type_, value)) == []

    def test_networks_only_where_taken(self):
        assert vendors.observables(record("ip-dst", "198.51.100.0/24")) == [
            ("ipv4", "198.51.100.0/24")
        ]
        assert (
            vendors.observables(
                record("ip-dst", "198.51.100.0/24"), single_addresses=True
            )
            == []
        )

    def test_score_severity_and_expiry(self):
        scored = record("ip-dst", "185.220.101.42", indicator={"score": 55})
        assert vendors.score(scored) == 55
        assert vendors.severity(scored) == "Medium"
        # No indicator: the event's threat level (1 is high).
        assert vendors.severity(record("ip-dst", "185.220.101.42")) == "High"
        # Last seen 2026-09-21: 30 days on.
        assert vendors.expiry(scored, 30, NOW).date().isoformat() == "2026-10-21"
        # Seen long ago: still a day from now, not in the past.
        old = record("ip-dst", "185.220.101.42", timestamp=1500000000)
        assert vendors.expiry(old, 30, NOW).isoformat() == "2026-10-16T12:00:00+00:00"

    def test_ids_are_stable(self):
        assert vendors.object_id("domain", "evil.example") == vendors.object_id(
            "domain", "evil.example"
        )
        assert vendors.object_id("domain", "evil.example") != vendors.object_id(
            "url", "evil.example"
        )

    def test_stix_patterns_escape(self):
        assert (
            vendors.stix_pattern("url", "http://x/a'b\\c")
            == "[url:value = 'http://x/a\\'b\\\\c']"
        )
        assert vendors.stix_pattern("sha256", "ab") == "[file:hashes.'SHA-256' = 'ab']"


class TestSentinel:
    def test_upload(self, api):
        api.on("POST", UPLOAD, (200, "", {}))
        transport = sentinel(api)
        transport.send(
            [
                record("domain|ip", "evil.example|185.220.101.42"),
                record("sha256", "a" * 64, indicator={"score": 40, "tlp": "tlp:green"}),
            ]
        )
        (token,) = api.calls("POST", "/tenant.example/oauth2/v2.0/token")
        assert parse_qs(token["body"]) == {
            "grant_type": ["client_credentials"],
            "client_id": ["app-id"],
            "client_secret": ["app-secret"],
            "scope": ["https://management.azure.com/.default"],
        }
        (upload,) = api.calls("POST", UPLOAD)
        assert upload["query"] == {"api-version": ["2024-02-01-preview"]}
        assert upload["headers"]["Authorization"] == f"Bearer {TOKEN}"
        body = json.loads(upload["body"])
        assert body["sourcesystem"] == "misp-workbench"
        patterns = [o["pattern"] for o in body["stixobjects"]]
        assert patterns == [
            "[domain-name:value = 'evil.example']",
            "[ipv4-addr:value = '185.220.101.42']",
            f"[file:hashes.'SHA-256' = '{'a' * 64}']",
        ]
        domain, _, sha = body["stixobjects"]
        assert domain["id"] == (
            f"indicator--{vendors.object_id('domain', 'evil.example')}"
        )
        assert domain["confidence"] == 85
        assert domain["valid_until"] == "2026-10-21T14:13:20.000Z"
        assert domain["object_marking_refs"] == [vendors.TLP_MARKINGS["tlp:amber"]]
        assert sha["confidence"] == 40
        assert sha["object_marking_refs"] == [vendors.TLP_MARKINGS["tlp:green"]]
        assert "revoked" not in domain

    def test_a_removal_expires_the_indicator(self, api):
        api.on("POST", UPLOAD, (200, "", {}))
        sentinel(api).send([removal("domain", "evil.example")])
        (stix,) = json.loads(api.calls("POST", UPLOAD)[0]["body"])["stixobjects"]
        # Revoking is permanent in STIX; the value may come back.
        assert "revoked" not in stix
        assert stix["valid_until"] == "2026-10-15T12:00:00.000Z"
        assert stix["valid_from"] < stix["valid_until"]
        assert stix["id"] == f"indicator--{vendors.object_id('domain', 'evil.example')}"

    def test_a_hundred_a_request(self, api):
        api.on("POST", UPLOAD, (200, "", {}))
        sentinel(api).send(
            [record("ip-dst", f"198.51.{i // 250}.{i % 250 + 1}") for i in range(250)]
        )
        sizes = [
            len(json.loads(c["body"])["stixobjects"]) for c in api.calls("POST", UPLOAD)
        ]
        assert sizes == [100, 100, 50]
        # One token for the delivery.
        assert len(api.calls("POST", "/tenant.example/oauth2/v2.0/token")) == 1

    def test_rejected_objects_fail_the_delivery(self, api):
        api.on("POST", UPLOAD, (200, fixture("sentinel_upload_errors.json"), {}))
        with pytest.raises(SinkDeliveryError, match="rejected 1 of 2 .*url"):
            sentinel(api).send(
                [
                    record("ip-dst", "185.220.101.42"),
                    record("url", "http://evil.example/x"),
                ]
            )

    def test_throttled_requests_wait_as_asked(self, api, no_waiting):
        throttled = (429, fixture("sentinel_throttled.json"), {})
        api.on("POST", UPLOAD, throttled, throttled, (200, "", {}))
        sentinel(api).send([record("ip-dst", "185.220.101.42")])
        assert no_waiting == [7.0, 7.0]
        assert len(api.calls("POST", UPLOAD)) == 3

    def test_throttled_too_long_fails(self, api):
        api.on("POST", UPLOAD, (429, "", {"Retry-After": "120"}))
        with pytest.raises(SinkDeliveryError, match="HTTP 429"):
            sentinel(api).send([record("ip-dst", "185.220.101.42")])
        assert len(api.calls("POST", UPLOAD)) == vendors.MAX_ATTEMPTS

    def test_check_only_asks_for_a_token(self, api):
        transport = sentinel(api)
        transport.check()
        assert api.calls("POST", UPLOAD) == []
        assert len(api.calls()) == 1

    def test_bad_credentials(self, api):
        api.on(
            "POST",
            "/tenant.example/oauth2/v2.0/token",
            (401, '{"error": "invalid_client"}', {}),
        )
        transport = vendors.SentinelTransport(
            sink_schemas.validate_config(
                "sentinel",
                {
                    "tenant_id": "tenant.example",
                    "client_id": "app-id",
                    "client_secret": "wrong",
                    "login_url": api.url,
                    "workspace_id": WORKSPACE,
                    "api_url": api.url,
                },
            )
        )
        with pytest.raises(SinkDeliveryError, match="token request answered HTTP 401$"):
            transport.check()

    def test_redirects_are_not_followed(self, api):
        api.on(
            "POST",
            "/tenant.example/oauth2/v2.0/token",
            (302, "", {"Location": "http://attacker.example/steal"}),
        )
        cfg = sink_schemas.validate_config(
            "sentinel",
            {
                "tenant_id": "tenant.example",
                "client_id": "app-id",
                "client_secret": "app-secret",
                "login_url": api.url,
                "workspace_id": WORKSPACE,
                "api_url": api.url,
            },
        )
        with pytest.raises(SinkDeliveryError, match="HTTP 302"):
            vendors.SentinelTransport(cfg).check()


class TestDefender:
    IMPORT = "/api/indicators/import"

    def test_import(self, api):
        api.on("POST", self.IMPORT, (200, json.dumps({"value": []}), {}))
        defender(api, action="block", rbac_group_names=["servers"]).send(
            [
                record("domain|ip", "evil.example|185.220.101.42"),
                record("sha256", "a" * 64),
                # Not for Defender: a network, a private address.
                record("ip-dst", "198.51.100.0/24"),
                record("ip-dst", "10.1.2.3"),
            ]
        )
        (token,) = api.calls("POST", "/tenant.example/oauth2/v2.0/token")
        assert parse_qs(token["body"])["scope"] == [
            "https://api.securitycenter.microsoft.com/.default"
        ]
        (call,) = api.calls("POST", self.IMPORT)
        indicators = json.loads(call["body"])["Indicators"]
        assert [
            (i["indicatorType"], i["indicatorValue"], i["action"]) for i in indicators
        ] == [
            ("DomainName", "evil.example", "Block"),
            ("IpAddress", "185.220.101.42", "Block"),
            ("FileSha256", "a" * 64, "BlockAndRemediate"),
        ]
        first = indicators[0]
        assert first["generateAlert"] is True
        assert first["severity"] == "High"
        assert first["application"] == "misp-workbench"
        assert first["rbacGroupNames"] == ["servers"]
        assert first["expirationTime"] == "2026-10-21T14:13:20.000Z"
        assert first["title"] == "C2 report"

    @pytest.mark.parametrize(
        "action,expected,alert",
        [("audit", "Audit", False), ("alert", "Audit", True), ("block", "Block", True)],
    )
    def test_actions(self, action, expected, alert):
        cfg = sink_schemas.validate_config(
            "defender",
            {
                "tenant_id": "t",
                "client_id": "c",
                "client_secret": "s",
                "action": action,
            },
        )
        (indicator,) = vendors.defender_indicators(
            record("domain", "evil.example"), cfg, NOW
        )
        assert (indicator["action"], indicator["generateAlert"]) == (expected, alert)

    def test_failed_imports_fail_the_delivery(self, api):
        api.on("POST", self.IMPORT, (200, fixture("defender_import.json"), {}))
        with pytest.raises(SinkDeliveryError, match="rejected 1 of 2 .*limit reached"):
            defender(api).send(
                [record("domain", "evil.example"), record("ip-dst", "185.220.101.42")]
            )

    def test_five_hundred_a_call(self, api):
        api.on("POST", self.IMPORT, (200, json.dumps({"value": []}), {}))
        defender(api).send([record("sha1", f"{i:040x}") for i in range(1, 1201)])
        sizes = [
            len(json.loads(c["body"])["Indicators"])
            for c in api.calls("POST", self.IMPORT)
        ]
        assert sizes == [500, 500, 200]

    def test_removals_delete_only_this_applications_indicators(self, api):
        api.on("GET", "/api/indicators", (200, fixture("defender_list.json"), {}))
        api.on("POST", "/api/indicators/BatchDelete", (204, "", {}))
        defender(api).send(
            [
                removal("ip-dst", "185.220.101.42"),
                # Not one of ours: nothing to delete.
                removal("domain", "someone-elses.example"),
            ]
        )
        (listing,) = api.calls("GET", "/api/indicators")
        assert listing["query"]["$filter"] == ["application eq 'misp-workbench'"]
        (delete,) = api.calls("POST", "/api/indicators/BatchDelete")
        assert json.loads(delete["body"]) == {"IndicatorIds": ["995"]}
        assert api.calls("POST", self.IMPORT) == []

    def test_gone_already_is_fine(self, api):
        api.on("GET", "/api/indicators", (200, fixture("defender_list.json"), {}))
        api.on("POST", "/api/indicators/BatchDelete", (404, "", {}))
        defender(api).send([removal("domain", "evil.example")])

    def test_application_is_quoted(self, api):
        api.on("GET", "/api/indicators", (200, json.dumps({"value": []}), {}))
        defender(api, application="o'brien").send([removal("domain", "evil.example")])
        (listing,) = api.calls("GET", "/api/indicators")
        assert listing["query"]["$filter"] == ["application eq 'o''brien'"]

    def test_check_reads_indicators(self, api):
        api.on("GET", "/api/indicators", (200, json.dumps({"value": []}), {}))
        defender(api).check()
        (call,) = api.calls("GET", "/api/indicators")
        assert call["query"]["$top"] == ["1"]
        assert api.calls("POST", self.IMPORT) == []


class TestElastic:
    def transport(self, api, **config):
        cfg = sink_schemas.validate_config("elastic", {"url": api.url, **config})
        if ("HEAD", "/misp-workbench-indicators") not in api.routes:
            api.on("HEAD", "/misp-workbench-indicators", (200, "", {}))
        return vendors.ElasticTransport(cfg, now=lambda: NOW)

    def test_creates_the_index_with_ecs_types(self, api):
        api.on("HEAD", "/misp-workbench-indicators", (404, "", {}))
        api.on("PUT", "/misp-workbench-indicators", (200, '{"acknowledged": true}', {}))
        api.on("POST", "/_bulk", (200, json.dumps({"errors": False, "items": []}), {}))
        transport = self.transport(api)
        transport.send([record("ip-dst", "185.220.101.42")])
        transport.send([record("ip-dst", "185.220.101.43")])
        (create,) = api.calls("PUT", "/misp-workbench-indicators")
        mappings = json.loads(create["body"])["mappings"]["properties"]
        indicator = mappings["threat"]["properties"]["indicator"]["properties"]
        assert indicator["ip"] == {"type": "ip"}
        assert indicator["url"]["properties"]["domain"] == {"type": "keyword"}
        # Looked up once per transport.
        assert len(api.calls("HEAD", "/misp-workbench-indicators")) == 1

    def test_an_existing_index_is_left_alone(self, api):
        api.on("POST", "/_bulk", (200, json.dumps({"errors": False, "items": []}), {}))
        self.transport(api).send([record("ip-dst", "185.220.101.42")])
        assert api.calls("PUT") == []

    def test_bulk(self, api):
        api.on("POST", "/_bulk", (200, json.dumps({"errors": False, "items": []}), {}))
        self.transport(api, api_key="a2V5OnNlY3JldA==").send(
            [
                record(
                    "domain|ip",
                    "evil.example|185.220.101.42",
                    indicator={"score": 75, "sources": ["CIRCL"]},
                ),
                record("md5", "d41d8cd98f00b204e9800998ecf8427e"),
                removal("url", "http://evil.example/x"),
            ]
        )
        (call,) = api.calls("POST", "/_bulk")
        assert call["headers"]["Authorization"] == "ApiKey a2V5OnNlY3JldA=="
        assert call["headers"]["Content-Type"] == "application/x-ndjson"
        lines = [json.loads(line) for line in call["body"].splitlines()]
        actions = [line for line in lines if "index" in line or "delete" in line]
        docs = [line for line in lines if "threat" in line]
        assert [(next(iter(a)), a[next(iter(a))]["_id"]) for a in actions] == [
            ("index", vendors.object_id("domain", "evil.example")),
            ("index", vendors.object_id("ipv4", "185.220.101.42")),
            ("index", vendors.object_id("md5", "d41d8cd98f00b204e9800998ecf8427e")),
            ("delete", vendors.object_id("url", "http://evil.example/x")),
        ]
        assert all(
            a[next(iter(a))]["_index"] == "misp-workbench-indicators" for a in actions
        )
        domain, ip, md5 = (d["threat"]["indicator"] for d in docs)
        assert domain["type"] == "domain-name"
        assert domain["url"] == {"domain": "evil.example"}
        assert domain["confidence"] == "High"
        assert domain["provider"] == "CIRCL"
        assert domain["marking"] == {"tlp": "AMBER"}
        assert ip == {**ip, "type": "ipv4-addr", "ip": "185.220.101.42"}
        assert md5["file"] == {"hash": {"md5": "d41d8cd98f00b204e9800998ecf8427e"}}
        assert docs[0]["event"]["kind"] == "enrichment"
        assert docs[0]["event"]["type"] == ["indicator"]
        assert docs[0]["@timestamp"] == "2026-10-15T12:00:00.000Z"

    def test_basic_auth(self, api):
        api.on("POST", "/_bulk", (200, json.dumps({"errors": False, "items": []}), {}))
        self.transport(api, username="writer", password="pw").send(
            [record("ip-dst", "185.220.101.42")]
        )
        (call,) = api.calls("POST", "/_bulk")
        assert call["headers"]["Authorization"] == "Basic d3JpdGVyOnB3"

    def test_item_errors_fail_but_missing_deletes_dont(self, api):
        api.on("POST", "/_bulk", (200, fixture("elastic_bulk.json"), {}))
        with pytest.raises(
            SinkDeliveryError,
            match="rejected 1 of 3 indicators: document_parsing_exception",
        ):
            self.transport(api).send([record("ip-dst", "185.220.101.42")])

    def test_check(self, api):
        api.on(
            "GET",
            "/_security/_authenticate",
            (200, fixture("elastic_authenticate.json"), {}),
        )
        self.transport(api, api_key="k").check()
        assert api.calls("POST", "/_bulk") == []

    @pytest.mark.parametrize("index", ["Upper", "_hidden", "a,b", "logs-*", ""])
    def test_index_names(self, index):
        with pytest.raises(sink_schemas.InvalidSinkConfig, match="index"):
            sink_schemas.validate_config(
                "elastic", {"url": "http://e:9200", "index": index}
            )


class TestSinkConfig:
    def test_open_transport_knows_vendors(self):
        cfg = sink_schemas.validate_config("elastic", {"url": "http://e:9200"})
        transport = open_transport("elastic", cfg)
        assert isinstance(transport, vendors.ElasticTransport)
        transport.close()

    @pytest.mark.parametrize("tenant", ["a/b", "../x", "x?y", ""])
    def test_tenant_ids(self, tenant):
        with pytest.raises(sink_schemas.InvalidSinkConfig, match="tenant_id"):
            sink_schemas.validate_config(
                "defender",
                {"tenant_id": tenant, "client_id": "c", "client_secret": "s"},
            )

    def test_sentinel_source_system_reserved(self):
        with pytest.raises(sink_schemas.InvalidSinkConfig, match="reserved"):
            sink_schemas.validate_config(
                "sentinel",
                {
                    "tenant_id": "t",
                    "client_id": "c",
                    "client_secret": "s",
                    "workspace_id": WORKSPACE,
                    "source_system": "Microsoft Sentinel",
                },
            )

    def test_secrets_are_masked(self):
        sink = sink_schemas.Sink(
            id=1,
            name="x",
            type="elastic",
            config={"url": "http://e:9200", "api_key": "k", "password": "p"},
            created_at=NOW,
        )
        assert sink.config["api_key"] == sink_schemas.SECRET_MASK
        assert sink.config["password"] == sink_schemas.SECRET_MASK

    @pytest.mark.parametrize(
        "field,value",
        [
            ("login_url", "https://attacker.example"),
            ("api_url", "https://attacker.example"),
            ("tenant_id", "other.example"),
            ("client_id", "other-app"),
            ("scope", "https://graph.microsoft.com/.default"),
        ],
    )
    def test_secret_stays_with_its_connection(self, field, value):
        stored = sink_schemas.validate_config(
            "defender", {"tenant_id": "t", "client_id": "c", "client_secret": "s"}
        )
        incoming = {**stored, "client_secret": sink_schemas.SECRET_MASK, field: value}
        with pytest.raises(sinks_repository.SecretRequired, match="client_secret"):
            sinks_repository._merge_secrets("defender", stored, incoming)
        # Unchanged, the masked secret is kept.
        kept = sinks_repository._merge_secrets(
            "defender", stored, {**stored, "client_secret": sink_schemas.SECRET_MASK}
        )
        assert kept["client_secret"] == "s"
