import runpy
from unittest.mock import MagicMock, patch

import pytest
import requests

import update_connection as uc


def _build_resp(payload):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


@patch("update_connection.requests.get")
def test_get_connection_fetches_resource(mock_get):
    mock_get.return_value = _build_resp({"ID": "123"})
    out = uc.get_connection("123", "https://src", {"h": "v"})

    assert out["ID"] == "123"
    mock_get.assert_called_once_with(
        "https://src/v1/gateway/inboundRoutes/123", headers={"h": "v"}
    )


@patch("update_connection.requests.put")
def test_update_connection_put(mock_put):
    uc.TARGET_ENV_URL = "https://target.test.com"
    uc.TARGET_ACCOUNT_HEADERS = {"h": "t"}
    mock_put.return_value = _build_resp({"ID": "target"})
    payload = {"ID": "target", "name": "foo", "mode": "INGRESS"}
    out = uc.update_connection("target", payload)

    assert out["ID"] == "target"
    mock_put.assert_called_once_with(
        "https://target.test.com/v1/gateway/inboundRoutes/target",
        json=payload,
        headers={"h": "t"},
    )


def test_transform_connection_payload_strips_fields():
    source = {
        "ID": "source",
        "vaultID": "sourceVault",
        "BasicAudit": {"foo": "bar"},
        "routes": [{"name": "r1", "invocationURL": "https://invoke"}],
    }
    target = {"ID": "target", "vaultID": "targetVault"}

    result = uc.transform_connection_payload(source, target)
    assert result["ID"] == "target"
    assert result["vaultID"] == "targetVault"
    assert "BasicAudit" not in result
    assert "invocationURL" not in result["routes"][0]
    # ensure source dict left untouched
    assert "BasicAudit" in source
    assert "invocationURL" in source["routes"][0]


@patch("update_connection.requests.put")
@patch("update_connection.requests.get")
def test_main_happy_path(mock_get, mock_put, monkeypatch):
    monkeypatch.setattr(uc, "SOURCE_CONNECTION_ID", "s1", raising=False)
    monkeypatch.setattr(uc, "TARGET_CONNECTION_ID", "t1", raising=False)
    monkeypatch.setattr(uc, "SOURCE_ENV_URL", "https://source", raising=False)
    monkeypatch.setattr(uc, "TARGET_ENV_URL", "https://target", raising=False)
    monkeypatch.setattr(uc, "SOURCE_ACCOUNT_HEADERS", {"h": "s"}, raising=False)
    monkeypatch.setattr(uc, "TARGET_ACCOUNT_HEADERS", {"h": "t"}, raising=False)

    mock_get.side_effect = [
        _build_resp(
            {
                "ID": "s1",
                "vaultID": "v1",
                "mode": "INGRESS",
                "BasicAudit": {},
                "routes": [{"invocationURL": "https://invoke"}],
            }
        ),
        _build_resp({"ID": "t1", "vaultID": "v2", "routes": [{}]}),
    ]
    mock_put.return_value = _build_resp({"ID": "t1"})

    uc.main()

    _, kwargs = mock_put.call_args
    assert kwargs["json"]["ID"] == "t1"
    assert "BasicAudit" not in kwargs["json"]
    assert kwargs["json"]["vaultID"] == "v2"


def test_main_missing_ids(monkeypatch, capsys):
    monkeypatch.setattr(uc, "SOURCE_CONNECTION_ID", None, raising=False)
    monkeypatch.setattr(uc, "TARGET_CONNECTION_ID", None, raising=False)
    uc.main()
    captured = capsys.readouterr().out
    assert "Missing connection IDs" in captured


def test_main_http_error(monkeypatch):
    class Resp:
        content = b"fail"

    err = requests.exceptions.HTTPError(response=Resp())

    monkeypatch.setattr(uc, "SOURCE_CONNECTION_ID", "s1", raising=False)
    monkeypatch.setattr(uc, "TARGET_CONNECTION_ID", "t1", raising=False)
    monkeypatch.setattr(uc, "SOURCE_ENV_URL", "https://source", raising=False)
    monkeypatch.setattr(uc, "TARGET_ENV_URL", "https://target", raising=False)
    monkeypatch.setattr(uc, "SOURCE_ACCOUNT_HEADERS", {}, raising=False)
    monkeypatch.setattr(uc, "TARGET_ACCOUNT_HEADERS", {}, raising=False)
    monkeypatch.setattr(
        uc,
        "get_connection",
        lambda *_args, **_kwargs: {"ID": "x", "vaultID": "y", "routes": []},
    )
    monkeypatch.setattr(
        uc,
        "update_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(err),
        raising=False,
    )

    with pytest.raises(SystemExit) as excinfo:
        uc.main()
    assert excinfo.value.code == 1


def test_main_generic_exception(monkeypatch):
    monkeypatch.setattr(uc, "SOURCE_CONNECTION_ID", "s1", raising=False)
    monkeypatch.setattr(uc, "TARGET_CONNECTION_ID", "t1", raising=False)
    monkeypatch.setattr(uc, "SOURCE_ENV_URL", "https://source", raising=False)
    monkeypatch.setattr(uc, "TARGET_ENV_URL", "https://target", raising=False)
    monkeypatch.setattr(uc, "SOURCE_ACCOUNT_HEADERS", {}, raising=False)
    monkeypatch.setattr(uc, "TARGET_ACCOUNT_HEADERS", {}, raising=False)
    monkeypatch.setattr(
        uc,
        "get_connection",
        lambda *_args, **_kwargs: {"ID": "x", "vaultID": "y", "routes": []},
    )
    monkeypatch.setattr(
        uc,
        "transform_connection_payload",
        lambda *_: (_ for _ in ()).throw(Exception("boom")),
    )

    with pytest.raises(SystemExit) as excinfo:
        uc.main()
    assert excinfo.value.code == 1


@patch("update_connection.requests.put")
@patch("update_connection.requests.get")
def test_run_as_script(mock_get, mock_put, monkeypatch):
    monkeypatch.setenv("SOURCE_CONNECTION_ID", "s1")
    monkeypatch.setenv("TARGET_CONNECTION_ID", "t1")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://source")
    monkeypatch.setenv("TARGET_ENV_URL", "https://target")
    monkeypatch.setenv("SOURCE_ACCOUNT_ID", "src")
    monkeypatch.setenv("TARGET_ACCOUNT_ID", "tgt")
    monkeypatch.setenv("SOURCE_ACCOUNT_AUTH", "sa")
    monkeypatch.setenv("TARGET_ACCOUNT_AUTH", "ta")

    mock_get.side_effect = [
        _build_resp({"ID": "s1", "vaultID": "v1", "mode": "INGRESS", "routes": []}),
        _build_resp({"ID": "t1", "vaultID": "v2", "routes": []}),
    ]
    mock_put.return_value = _build_resp({"ID": "t1"})

    runpy.run_module("update_connection", run_name="__main__")
    assert mock_put.called
