import pytest
from unittest.mock import MagicMock, patch

import update_policy as up


@patch("update_policy.requests.patch")
@patch("update_policy.requests.get")
def test_main_success(mock_get, mock_patch, monkeypatch):
    monkeypatch.setattr(up, "SOURCE_POLICY_ID", "s1", raising=False)
    monkeypatch.setattr(up, "TARGET_POLICY_ID", "t1", raising=False)
    monkeypatch.setattr(up, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(up, "TARGET_ENV_URL", "https://t")

    src = MagicMock(); src.raise_for_status.return_value = None; src.json.return_value = {"policy": {"name": "n", "displayName": "d", "description": "x", "rules": [{"ID": "r", "name": "R", "ruleExpression": "expr", "actions": ["POLICY.read"], "resources": ["vault:v/table:t/column:c"], "resourceType": "COLUMN", "dlpFormat": None}]}}
    tgt = MagicMock(); tgt.raise_for_status.return_value = None; tgt.json.return_value = {"policy": {"ID": "t1", "rules": [] , "resource": {"ID": "tv"}}}
    mock_get.side_effect = [src, tgt]

    p = MagicMock(); p.raise_for_status.return_value = None; p.json.return_value = {"ok": True}
    mock_patch.return_value = p

    up.main()
    assert mock_patch.called


def test_main_http_error(monkeypatch):
    import requests

    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    def raise_err(_):
        raise err

    monkeypatch.setattr(up, "SOURCE_POLICY_ID", "s1", raising=False)
    monkeypatch.setattr(up, "TARGET_POLICY_ID", "t1", raising=False)
    monkeypatch.setattr(up, "get_source_policy", raise_err)

    with pytest.raises(requests.exceptions.HTTPError):
        up.main()


def test_main_missing_inputs(monkeypatch):
    # Missing IDs should go to the "Please provide valid input" branch
    monkeypatch.setattr(up, "SOURCE_POLICY_ID", None, raising=False)
    monkeypatch.setattr(up, "TARGET_POLICY_ID", None, raising=False)
    with patch("update_policy.requests.get") as g, patch("update_policy.requests.patch") as p:
        result = up.main()
        assert result is None
        assert g.call_count == 0
        assert p.call_count == 0


def test_main_generic_exception(monkeypatch):
    # Cause a non-HTTP exception inside main to cover lines 155-157
    monkeypatch.setattr(up, "SOURCE_POLICY_ID", "s1", raising=False)
    monkeypatch.setattr(up, "TARGET_POLICY_ID", "t1", raising=False)
    monkeypatch.setattr(up, "get_source_policy", lambda _id: {"policy": {"rules": []}})
    monkeypatch.setattr(up, "get_target_policy", lambda _id: {"policy": {"ID": "t1", "rules": [], "resource": {"ID": "tv"}}})
    monkeypatch.setattr(up, "transform_policy_payload", lambda s, t: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(Exception):
        up.main()


def test_run_as_script(monkeypatch):
    # Cover __main__ guard (line 161)
    import runpy
    import requests as _requests

    monkeypatch.setenv("SOURCE_POLICY_ID", "s1")
    monkeypatch.setenv("TARGET_POLICY_ID", "t1")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://s")
    monkeypatch.setenv("TARGET_ENV_URL", "https://t")

    src = MagicMock(); src.raise_for_status.return_value = None; src.json.return_value = {"policy": {"name": "n", "displayName": "d", "description": "x", "rules": []}}
    tgt = MagicMock(); tgt.raise_for_status.return_value = None; tgt.json.return_value = {"policy": {"ID": "t1", "rules": [], "resource": {"ID": "tv"}}}
    patch_resp = MagicMock(); patch_resp.raise_for_status.return_value = None; patch_resp.json.return_value = {"ok": True}
    with patch.object(_requests, "get", side_effect=[src, tgt]) as mget, patch.object(_requests, "patch", return_value=patch_resp) as mpatch:
        runpy.run_module("update_policy", run_name="__main__")
        assert mget.call_count == 2
        assert mpatch.call_count == 1
