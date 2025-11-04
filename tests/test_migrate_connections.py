import pytest
from unittest.mock import MagicMock, patch, mock_open

import migrate_connections as mc


def test_transform_connection_payload_removes_audit_and_invocation(monkeypatch):
    monkeypatch.setattr(mc, "TARGET_VAULT_ID", "target-vault")
    source = {
        "ID": "c1",
        "name": "Conn",
        "mode": "EGRESS",
        "vaultID": "source-vault",
        "routes": [{"path": "/x", "method": "GET", "invocationURL": "https://example"}],
        "BasicAudit": {"CreatedBy": "u"},
    }
    out = mc.transform_connection_payload(source)
    assert out["vaultID"] == "target-vault"
    assert "BasicAudit" not in out
    assert "invocationURL" not in out["routes"][0]


@patch("migrate_connections.requests.post")
def test_main_with_config_creates_connection(mock_post, monkeypatch, tmp_path):
    # Ensure config branch is used
    monkeypatch.setattr(mc, "CONNECTIONS_CONFIG", "config_file", raising=False)
    # Ensure vault target is set for transform
    monkeypatch.setattr(mc, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mc, "TARGET_ENV_URL", "https://target")
    # mock POST response
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"ID": "new-conn"}
    mock_post.return_value = resp

    # Mock file read of connections config
    sample = (
        "[\n"
        "  {\n"
        '    "ID": "c1", "name": "Conn", "mode": "EGRESS", "vaultID": "sv",\n'
        '    "routes": [{"path": "/p", "method": "GET", "invocationURL": "u"}]\n'
        "  }\n"
        "]"
    )
    with patch("builtins.open", mock_open(read_data=sample)):
        mc.main()

    # Should attempt to create connections from config (>=1)
    assert mock_post.call_count >= 1


@patch("migrate_connections.requests.get")
@patch("migrate_connections.requests.post")
def test_main_with_ids_fetches_each_and_creates(mock_post, mock_get, monkeypatch):
    monkeypatch.setattr(mc, "CONNECTIONS_CONFIG", None, raising=False)
    monkeypatch.setattr(mc, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mc, "SOURCE_ENV_URL", "https://source")
    monkeypatch.setattr(mc, "TARGET_ENV_URL", "https://target")

    # GET returns one connection
    get_resp = MagicMock()
    get_resp.raise_for_status.return_value = None
    get_resp.json.return_value = {
        "ID": "abc",
        "name": "ConnA",
        "mode": "EGRESS",
        "vaultID": "sv",
        "routes": [{"path": "/p", "method": "GET", "invocationURL": "u"}],
    }
    mock_get.return_value = get_resp

    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.json.return_value = {"ID": "new"}
    mock_post.return_value = post_resp

    mc.main(connection_ids=["abc"])
    assert mock_get.call_count >= 1
    assert mock_post.call_count == 1


def test_main_migrate_all_without_source_vault(monkeypatch):
    monkeypatch.setattr(mc, "MIGRATE_ALL_CONNECTIONS", "true", raising=False)
    # Ensure SOURCE_VAULT_ID not set in module constant; no action expected
    monkeypatch.setattr(mc, "SOURCE_VAULT_ID", None, raising=False)
    # Call main and ensure it exits early without raising
    assert mc.main(connection_ids=[]) is None


@patch("migrate_connections.requests.get")
def test_main_handles_http_error(mock_get, monkeypatch):
    import requests

    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    def raise_err(*args, **kwargs):
        raise err

    monkeypatch.setattr(mc, "CONNECTIONS_CONFIG", None, raising=False)
    monkeypatch.setattr(mc, "CONNECTION_IDS", "['abc']", raising=False)
    monkeypatch.setattr(mc, "SOURCE_ENV_URL", "https://s")
    mock_get.side_effect = raise_err

    with pytest.raises(requests.exceptions.HTTPError):
        mc.main()


def test_main_migrate_all_with_source_calls_list(monkeypatch):
    # Cover MIGRATE_ALL branch when SOURCE_VAULT_ID present (lines 87-88)
    monkeypatch.setattr(mc, "MIGRATE_ALL_CONNECTIONS", "true", raising=False)
    monkeypatch.setattr(mc, "SOURCE_VAULT_ID", "sv", raising=False)
    called = {"hit": False}

    def fake_list(v):
        called["hit"] = True
        return []

    monkeypatch.setattr(mc, "list_connections", fake_list)
    mc.main()
    assert called["hit"] is True


def test_main_other_exception_branch(monkeypatch):
    # Trigger generic Exception path (lines 126-128)
    monkeypatch.setattr(mc, "CONNECTIONS_CONFIG", None, raising=False)
    monkeypatch.setattr(mc, "CONNECTION_IDS", "['x']", raising=False)

    def boom(_):
        raise Exception("boom")

    monkeypatch.setattr(mc, "get_connection", boom)
    with pytest.raises(Exception):
        mc.main()


def test_run_as_script_config_file(monkeypatch):
    # Execute module under __main__ to cover line 132
    import runpy
    import requests as _requests

    monkeypatch.setenv("CONNECTIONS_CONFIG", "config_file")
    monkeypatch.setenv("TARGET_ENV_URL", "https://t")
    monkeypatch.setenv("TARGET_ACCOUNT_ID", "acc")
    monkeypatch.setenv("TARGET_ACCOUNT_AUTH", "tok")
    monkeypatch.setenv("SOURCE_ACCOUNT_ID", "sacc")
    monkeypatch.setenv("SOURCE_ACCOUNT_AUTH", "stok")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://s")
    sample = '[\n  {\n    "ID": "c1", "name": "Conn", "mode": "EGRESS", "vaultID": "sv",\n    "routes": [{"path": "/p", "method": "GET", "invocationURL": "u"}]\n  }\n]'
    with patch("builtins.open", mock_open(read_data=sample)):
        with patch.object(_requests, "post") as mpost:
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = {"ID": "new"}
            mpost.return_value = r
            runpy.run_module("migrate_connections", run_name="__main__")
            assert mpost.call_count >= 1


@patch("migrate_connections.requests.get")
def test_list_connections_combines_inbound_and_outbound(mock_get, monkeypatch):
    monkeypatch.setattr(mc, "SOURCE_ENV_URL", "https://s")
    r1 = MagicMock()
    r1.raise_for_status.return_value = None
    r1.json.return_value = {"ConnectionMappings": ["o1"]}
    r2 = MagicMock()
    r2.raise_for_status.return_value = None
    r2.json.return_value = {"ConnectionMappings": ["i1"]}
    mock_get.side_effect = [r1, r2]
    out = mc.list_connections("v")
    assert out == ["o1", "i1"]


@patch("migrate_connections.requests.get")
def test_get_connection_returns_json(mock_get, monkeypatch):
    monkeypatch.setattr(mc, "SOURCE_ENV_URL", "https://s")
    g = MagicMock()
    g.raise_for_status.return_value = None
    g.json.return_value = {"ID": "c"}
    mock_get.return_value = g
    out = mc.get_connection("c")
    assert out["ID"] == "c"


@patch("migrate_connections.requests.post")
def test_main_handles_creation_failure(mock_post, monkeypatch):
    # Drive config file path
    monkeypatch.setattr(mc, "CONNECTIONS_CONFIG", "config_file", raising=False)
    monkeypatch.setattr(mc, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mc, "TARGET_ENV_URL", "https://t")

    fail = MagicMock()
    fail.status_code = 500
    fail.content = b"err"
    mock_post.return_value = fail

    sample = (
        "[\n"
        "  {\n"
        '    "ID": "c1", "name": "Conn", "mode": "INGRESS", "vaultID": "sv",\n'
        '    "routes": [{"path": "/p", "method": "GET", "invocationURL": "u"}]\n'
        "  }\n"
        "]"
    )
    with patch("builtins.open", mock_open(read_data=sample)):
        mc.main()
        # Should attempt to create the connection once even if it fails
        assert mock_post.call_count == 1
