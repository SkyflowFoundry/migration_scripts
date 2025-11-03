import pytest
import requests
from unittest.mock import MagicMock, patch

import migrate_service_accounts as msa


def test_transform_service_account_payload_strips_fields():
    source = {
        "serviceAccount": {
            "ID": "sid",
            "namespace": "ns",
            "BasicAudit": {},
            "name": "n",
        }
    }
    out = msa.transform_service_account_payload(source)
    svc = out["serviceAccount"]
    assert "ID" not in svc and "namespace" not in svc and "BasicAudit" not in svc


@patch("migrate_service_accounts.migrate_roles")
@patch("migrate_service_accounts.requests.post")
@patch("migrate_service_accounts.requests.get")
def test_main_creates_sa_and_assigns_roles(mock_get, mock_post, mock_migrate_roles, monkeypatch):
    monkeypatch.setattr(msa, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(msa, "TARGET_ENV_URL", "https://t")

    get_sa = MagicMock()
    get_sa.raise_for_status.return_value = None
    get_sa.json.return_value = {
        "serviceAccount": {
            "ID": "orig-sa",
            "namespace": "ns",
            "BasicAudit": {},
            "name": "SA",
        }
    }

    list_roles = MagicMock()
    list_roles.raise_for_status.return_value = None
    list_roles.json.return_value = {
        "roleToResource": [
            {"role": {"ID": "r1"}},
            {"role": {"ID": "r2"}},
        ]
    }

    mock_get.side_effect = [get_sa, list_roles]

    create_sa = MagicMock()
    create_sa.raise_for_status.return_value = None
    create_sa.json.return_value = {"clientID": "new-sa"}

    assign_role = MagicMock()
    assign_role.raise_for_status.return_value = None

    mock_post.side_effect = [create_sa, assign_role, assign_role]

    mock_migrate_roles.return_value = [{"ID": "nr1"}, {"ID": "nr2"}]

    created = msa.main(service_accounts_ids=["sa1"])
    assert created and created[0]["clientID"] == "new-sa"

@patch("migrate_service_accounts.requests.post")
@patch("migrate_service_accounts.requests.get")
def test_main_no_roles_found(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(msa, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(msa, "TARGET_ENV_URL", "https://t")
    monkeypatch.setattr(msa, "SERVICE_ACCOUNT_IDS", "['sa1']", raising=False)

    get_sa = MagicMock(); get_sa.raise_for_status.return_value = None; get_sa.json.return_value = {"serviceAccount": {"ID": "orig", "namespace": "n", "BasicAudit": {}, "name": "SA"}}
    list_empty = MagicMock(); list_empty.raise_for_status.return_value = None; list_empty.json.return_value = {"roleToResource": []}
    mock_get.side_effect = [get_sa, list_empty]

    create_sa = MagicMock(); create_sa.raise_for_status.return_value = None; create_sa.json.return_value = {"clientID": "new-sa"}
    mock_post.return_value = create_sa

    out = msa.main()
    assert out and out[0]["clientID"] == "new-sa"


def test_main_http_error(monkeypatch):
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    def raise_err(_):
        raise err

    monkeypatch.setattr(msa, "SERVICE_ACCOUNT_IDS", "['sa1']", raising=False)
    monkeypatch.setattr(msa, "get_service_account", raise_err)
    with pytest.raises(requests.exceptions.HTTPError):
        msa.main()


def test_generic_exception_branch(monkeypatch):
    # Trigger generic except (122-124)
    monkeypatch.setattr(msa, "SERVICE_ACCOUNT_IDS", "['sa1']", raising=False)
    monkeypatch.setattr(msa, "get_service_account", lambda _id: {"serviceAccount": {"ID": "orig", "namespace": "n", "BasicAudit": {}, "name": "SA"}})
    monkeypatch.setattr(msa, "transform_service_account_payload", lambda x: x)
    monkeypatch.setattr(msa, "create_service_account", lambda x: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(Exception):
        msa.main()


def test_run_as_script(monkeypatch):
    # Cover line 128
    import runpy
    import requests as _requests
    monkeypatch.setenv("SERVICE_ACCOUNT_IDS", "[]")
    with patch.object(_requests, "get") as g, patch.object(_requests, "post") as p:
        runpy.run_module("migrate_service_accounts", run_name="__main__")
        # ROLE_IDS is [], so no network calls should be made
        assert g.call_count == 0
        assert p.call_count == 0
