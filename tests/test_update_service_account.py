import pytest
import requests
from unittest.mock import MagicMock, patch

import update_service_account as usa


def test_transform_service_account_payload_builds(monkeypatch):
    source = {
        "serviceAccount": {"name": "S", "displayName": "SD", "description": "Desc"},
        "clientConfiguration": {
            "enforceContextID": True,
            "enforceSignedDataTokens": False,
        },
    }
    target = {"serviceAccount": {"ID": "tid"}}
    out = usa.transform_service_account_payload(source, target)
    assert out["ID"] == "tid"
    assert out["serviceAccount"]["name"] == "S"
    assert out["clientConfiguration"]["enforceContextID"] is True


@patch("update_service_account.requests.post")
@patch("update_service_account.requests.get")
@patch("update_service_account.requests.patch")
def test_main_update_metadata(mock_patch, mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(usa, "SOURCE_SERVICE_ACCOUNT_ID", "s1", raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", "t1", raising=False)
    monkeypatch.setattr(usa, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(usa, "TARGET_ENV_URL", "https://t")

    g1 = MagicMock(); g1.raise_for_status.return_value = None; g1.json.return_value = {"serviceAccount": {"name": "S", "displayName": "SD", "description": "Desc"}, "clientConfiguration": {"enforceContextID": True, "enforceSignedDataTokens": False}}
    g2 = MagicMock(); g2.raise_for_status.return_value = None; g2.json.return_value = {"serviceAccount": {"ID": "t1"}}
    mock_get.side_effect = [g1, g2]

    p = MagicMock(); p.raise_for_status.return_value = None; p.json.return_value = {"ok": True}
    mock_patch.return_value = p

    usa.main()
    assert mock_patch.called


@patch("update_service_account.requests.post")
def test_main_assign_roles(mock_post, monkeypatch):
    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "ASSIGN_ROLES", raising=False)
    monkeypatch.setattr(usa, "ROLE_IDS", "['r1','r2']", raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", "t1", raising=False)

    r = MagicMock(); r.raise_for_status.return_value = None
    mock_post.return_value = r

    usa.main()
    assert mock_post.call_count == 2


@patch("update_service_account.requests.post")
def test_main_assign_roles_empty_list(mock_post, monkeypatch):
    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "ASSIGN_ROLES", raising=False)
    monkeypatch.setattr(usa, "ROLE_IDS", "[]", raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", "t1", raising=False)
    usa.main()
    assert mock_post.call_count == 0

def test_main_http_error_on_update(monkeypatch):
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(usa, "SOURCE_SERVICE_ACCOUNT_ID", "s1", raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", "t1", raising=False)
    monkeypatch.setattr(usa, "get_source_service_account", lambda _id: {"serviceAccount": {"name": "n", "displayName": "d", "description": "x"}, "clientConfiguration": {"enforceContextID": True, "enforceSignedDataTokens": False}})
    monkeypatch.setattr(usa, "get_target_service_account", lambda _id: {"serviceAccount": {"ID": "t1"}})

    def raise_err(_):
        raise err

    monkeypatch.setattr(usa, "update_service_account", raise_err)
    with pytest.raises(requests.exceptions.HTTPError):
        usa.main()


def test_main_update_metadata_missing_inputs(monkeypatch):
    # Missing IDs should trigger exit(1) (110-111)
    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(usa, "SOURCE_SERVICE_ACCOUNT_ID", None, raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", None, raising=False)
    with pytest.raises(SystemExit):
        usa.main()


def test_main_assign_roles_missing_ids(monkeypatch):
    # Missing ROLE_IDS triggers exit(1) (121-122)
    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "ASSIGN_ROLES", raising=False)
    monkeypatch.setattr(usa, "ROLE_IDS", None, raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", "t1", raising=False)
    with pytest.raises(SystemExit):
        usa.main()


def test_main_generic_exception(monkeypatch):
    # Cause generic exception to hit 132-134
    monkeypatch.setattr(usa, "UPDATE_SERVICE_ACCOUNT_CRITERIA", "UPDATE_METADATA", raising=False)
    monkeypatch.setattr(usa, "SOURCE_SERVICE_ACCOUNT_ID", "s1", raising=False)
    monkeypatch.setattr(usa, "TARGET_SERVICE_ACCOUNT_ID", "t1", raising=False)
    monkeypatch.setattr(usa, "get_source_service_account", lambda _id: {"serviceAccount": {"name": "n", "displayName": "d", "description": "x"}, "clientConfiguration": {"enforceContextID": True, "enforceSignedDataTokens": False}})
    monkeypatch.setattr(usa, "get_target_service_account", lambda _id: {"serviceAccount": {"ID": "t1"}})
    monkeypatch.setattr(usa, "update_service_account", lambda payload: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(Exception):
        usa.main()


def test_run_as_script(monkeypatch):
    # Cover __main__ guard (line 138)
    import runpy, requests as _requests
    monkeypatch.setenv("UPDATE_SERVICE_ACCOUNT_CRITERIA", "ASSIGN_ROLES")
    monkeypatch.setenv("ROLE_IDS", "[]")
    monkeypatch.setenv("TARGET_SERVICE_ACCOUNT_ID", "t1")
    with patch.object(_requests, "post") as p:
        runpy.run_module("update_service_account", run_name="__main__")
        # ROLE_IDS is [], so no role assignment posts should be made
        assert p.call_count == 0
