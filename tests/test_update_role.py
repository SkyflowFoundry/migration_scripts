import pytest
import requests
from unittest.mock import MagicMock, patch

import update_role as ur


def test_transform_role_payload_simple():
    source = {"role": {"definition": {"name": "N", "displayName": "D", "description": "Desc"}}}
    target = {"role": {"ID": "rid"}}
    out = ur.transform_role_payload(source, target)
    assert out["ID"] == "rid"
    assert out["roleDefinition"]["name"] == "N"


@patch("update_role.requests.post")
@patch("update_role.requests.get")
@patch("update_role.requests.patch")
def test_main_update_metadata(mock_patch, mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(ur, "SOURCE_ROLE_ID", "s1", raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", "t1", raising=False)
    monkeypatch.setattr(ur, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(ur, "TARGET_ENV_URL", "https://t")

    g1 = MagicMock(); g1.raise_for_status.return_value = None; g1.json.return_value = {"role": {"definition": {"name": "N", "displayName": "D", "description": "d"}}}
    g2 = MagicMock(); g2.raise_for_status.return_value = None; g2.json.return_value = {"role": {"ID": "t1"}}
    mock_get.side_effect = [g1, g2]

    p = MagicMock(); p.raise_for_status.return_value = None; p.json.return_value = {"ok": True}
    mock_patch.return_value = p

    ur.main()
    assert mock_patch.called


@patch("update_role.requests.post")
def test_main_assign_policy(mock_post, monkeypatch):
    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "ASSIGN_POLICY", raising=False)
    monkeypatch.setattr(ur, "POLICY_IDS", "['p1','p2']", raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", "t1", raising=False)

    r = MagicMock(); r.raise_for_status.return_value = None
    mock_post.return_value = r

    ur.main()
    # two posts for two policies
    assert mock_post.call_count == 2


@patch("update_role.requests.post")
def test_main_assign_policy_empty_list(mock_post, monkeypatch):
    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "ASSIGN_POLICY", raising=False)
    monkeypatch.setattr(ur, "POLICY_IDS", "[]", raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", "t1", raising=False)
    ur.main()
    assert mock_post.call_count == 0


def test_main_http_error_on_update(monkeypatch):
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(ur, "SOURCE_ROLE_ID", "s1", raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", "t1", raising=False)
    monkeypatch.setattr(ur, "get_source_role", lambda _id: {"role": {"definition": {"name": "n", "displayName": "d", "description": "x"}}})
    monkeypatch.setattr(ur, "get_target_role", lambda _id: {"role": {"ID": "t1"}})

    def raise_err(_):
        raise err

    monkeypatch.setattr(ur, "update_role", raise_err)
    with pytest.raises(requests.exceptions.HTTPError):
        ur.main()


def test_main_update_metadata_missing_inputs(monkeypatch):
    # Missing IDs should trigger exit(1) (lines 90-91)
    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(ur, "SOURCE_ROLE_ID", None, raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", None, raising=False)
    with pytest.raises(SystemExit):
        ur.main()


def test_main_assign_policy_missing_ids(monkeypatch):
    # Missing POLICY_IDS triggers exit(1) (101-102)
    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "ASSIGN_POLICY", raising=False)
    monkeypatch.setattr(ur, "POLICY_IDS", None, raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", "t1", raising=False)
    with pytest.raises(SystemExit):
        ur.main()


def test_main_generic_exception(monkeypatch):
    # Cause generic exception to hit 107-109
    monkeypatch.setattr(ur, "UPDATE_ROLE_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(ur, "SOURCE_ROLE_ID", "s1", raising=False)
    monkeypatch.setattr(ur, "TARGET_ROLE_ID", "t1", raising=False)
    monkeypatch.setattr(ur, "get_source_role", lambda _id: {"role": {"definition": {"name": "n", "displayName": "d", "description": "x"}}})
    monkeypatch.setattr(ur, "get_target_role", lambda _id: {"role": {"ID": "t1"}})
    monkeypatch.setattr(ur, "update_role", lambda payload: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(Exception):
        ur.main()


def test_run_as_script(monkeypatch):
    # Cover __main__ guard (line 113)
    import runpy, requests as _requests
    monkeypatch.setenv("UPDATE_ROLE_CRITERIA", "ASSIGN_POLICY")
    monkeypatch.setenv("POLICY_IDS", "[]")
    monkeypatch.setenv("TARGET_ROLE_ID", "t1")
    with patch.object(_requests, "post") as p:
        runpy.run_module("update_role", run_name="__main__")
        # POLICY_IDS is [], so no assignment posts should be made
        assert p.call_count == 0
