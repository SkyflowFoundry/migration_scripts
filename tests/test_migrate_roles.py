import pytest
import requests
from unittest.mock import MagicMock, patch

import migrate_roles as mr


def test_transform_role_payload_filters_upstream(monkeypatch):
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv")
    source = {
        "role": {
            "definition": {
                "permissions": [
                    "accounts.read:upstream",
                    "workspaces.read:upstream",
                    "vaults.read:upstream",
                    "policies.read",
                ]
            }
        }
    }
    out = mr.transform_role_payload(source)
    perms = out["roleDefinition"]["permissions"]
    assert "policies.read" in perms and all(
        p not in perms
        for p in [
            "accounts.read:upstream",
            "workspaces.read:upstream",
            "vaults.read:upstream",
        ]
    )
    assert out["resource"] == {"ID": "tv", "type": "VAULT"}


@patch("migrate_roles.requests.get")
def test_main_system_role_path(mock_get, monkeypatch):
    # Provide a ROLE_ID that resolves to a system role
    monkeypatch.setenv("ROLE_IDS", "['rid1']")
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")

    # First GET: get_role -> returns role with system name
    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {"role": {"definition": {"name": mr.SYSTEM_ROLES[0]}}}

    # Second GET: get_system_role -> returns existing role list
    sys_resp = MagicMock()
    sys_resp.raise_for_status.return_value = None
    sys_resp.json.return_value = {"roles": [{"ID": "sys-role"}]}

    mock_get.side_effect = [role_resp, sys_resp]
    # migrate_roles.main ignores the argument; provide ROLE_IDS module var
    monkeypatch.setattr(mr, "ROLE_IDS", "['rid1']", raising=False)
    out = mr.main()
    assert out and out[0]["ID"] == "sys-role"


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
@patch("migrate_roles.migrate_policies")
def test_main_custom_role_create_and_assign(
    mock_migrate_policies, mock_get, mock_post, monkeypatch
):
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")
    monkeypatch.setattr(mr, "SKIP_ROLE_CREATION_IF_ROLE_EXISTS", None, raising=False)
    monkeypatch.setattr(mr, "MIGRATE_ALL_ROLES", None, raising=False)

    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {
        "role": {"definition": {"name": "Custom", "permissions": ["policies.read"]}}
    }

    policies_resp = MagicMock()
    policies_resp.raise_for_status.return_value = None
    policies_resp.json.return_value = {"policies": [{"ID": "p1"}, {"ID": "p2"}]}

    # get_role -> role_resp, get_role_policies -> policies_resp
    mock_get.side_effect = [role_resp, policies_resp]

    create_post = MagicMock()
    create_post.raise_for_status.return_value = None
    create_post.json.return_value = {"ID": "new-role"}

    assign_post = MagicMock()
    assign_post.raise_for_status.return_value = None

    mock_post.side_effect = [create_post, assign_post, assign_post]

    mock_migrate_policies.return_value = [{"ID": "np1"}, {"ID": "np2"}]

    monkeypatch.setattr(mr, "ROLE_IDS", "['rid2']", raising=False)
    out = mr.main()
    assert out and any(r.get("ID") == "new-role" for r in out)


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
def test_migrate_all_roles_branch(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(mr, "MIGRATE_ALL_ROLES", "true", raising=False)
    monkeypatch.setattr(mr, "SOURCE_VAULT_ID", "sv", raising=False)
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv", raising=False)
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")

    list_resp = MagicMock()
    list_resp.raise_for_status.return_value = None
    list_resp.json.return_value = {"roles": [{"ID": "r1"}]}
    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {
        "role": {"definition": {"name": "Custom", "permissions": ["policies.read"]}}
    }
    no_policies = MagicMock()
    no_policies.raise_for_status.return_value = None
    no_policies.json.return_value = {"policies": []}
    mock_get.side_effect = [list_resp, role_resp, no_policies]

    create_post = MagicMock()
    create_post.raise_for_status.return_value = None
    create_post.json.return_value = {"ID": "new-role"}
    mock_post.return_value = create_post

    out = mr.main()
    assert out and any(r.get("ID") == "new-role" for r in out)


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
def test_skip_role_creation_if_exists(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(mr, "SKIP_ROLE_CREATION_IF_ROLE_EXISTS", "true", raising=False)
    monkeypatch.setattr(mr, "MIGRATE_ALL_ROLES", None, raising=False)
    monkeypatch.setattr(mr, "ROLE_IDS", "['rid']", raising=False)
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv", raising=False)
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")

    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {
        "role": {"definition": {"name": "Custom", "permissions": ["policies.read"]}}
    }
    exists_resp = MagicMock()
    exists_resp.raise_for_status.return_value = None
    exists_resp.json.return_value = {"roles": [{"ID": "existing"}]}
    mock_get.side_effect = [role_resp, exists_resp]

    mr.main()
    # No creation posts expected
    assert mock_post.call_count == 0


def test_main_http_error(monkeypatch):
    # Trigger HTTPError after role_name is known to avoid UnboundLocalError
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    # First call returns a SYSTEM role so role_name is set
    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {"role": {"definition": {"name": mr.SYSTEM_ROLES[0]}}}

    # get_system_role raises HTTPError
    def raise_err(*args, **kwargs):
        raise err

    monkeypatch.setattr(mr, "ROLE_IDS", "['rid']", raising=False)
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")
    monkeypatch.setattr(mr, "get_role", lambda _id: role_resp.json())
    monkeypatch.setattr(mr, "get_system_role", raise_err)
    with pytest.raises(requests.exceptions.HTTPError):
        mr.main()


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
def test_migrate_all_missing_source_prints(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(mr, "MIGRATE_ALL_ROLES", "true", raising=False)
    monkeypatch.setattr(mr, "SOURCE_VAULT_ID", None, raising=False)
    monkeypatch.setattr(mr, "ROLE_IDS", "[]", raising=False)
    # Function prints a message then later attempts to iterate None; assert it errors predictably
    with pytest.raises(TypeError):
        mr.main()


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
def test_custom_role_check_does_not_exist(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(mr, "SKIP_ROLE_CREATION_IF_ROLE_EXISTS", "true", raising=False)
    monkeypatch.setattr(mr, "MIGRATE_ALL_ROLES", None, raising=False)
    monkeypatch.setattr(mr, "ROLE_IDS", "['rid']", raising=False)
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv", raising=False)
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")

    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {
        "role": {"definition": {"name": "Custom", "permissions": ["policies.read"]}}
    }
    no_exist = MagicMock()
    no_exist.raise_for_status.return_value = None
    no_exist.json.return_value = {"roles": []}
    policies_empty = MagicMock()
    policies_empty.raise_for_status.return_value = None
    policies_empty.json.return_value = {"policies": []}
    mock_get.side_effect = [role_resp, no_exist, policies_empty]

    create_post = MagicMock()
    create_post.raise_for_status.return_value = None
    create_post.json.return_value = {"ID": "new-role"}
    mock_post.return_value = create_post

    out = mr.main()
    assert any(r.get("ID") == "new-role" for r in out)


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
def test_http_error_after_role_name(mock_get, mock_post, monkeypatch):
    # Raise HTTPError during create_role to hit lines 165-166
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    monkeypatch.setattr(mr, "ROLE_IDS", "['rid']", raising=False)
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")

    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {
        "role": {"definition": {"name": "Custom", "permissions": ["policies.read"]}}
    }
    policies_resp = MagicMock()
    policies_resp.raise_for_status.return_value = None
    policies_resp.json.return_value = {"policies": []}
    mock_get.side_effect = [role_resp, policies_resp]

    def raise_err(*args, **kwargs):
        raise err

    mock_post.side_effect = raise_err

    with pytest.raises(requests.exceptions.HTTPError):
        mr.main()


@patch("migrate_roles.requests.post")
@patch("migrate_roles.requests.get")
def test_generic_exception_after_role_name(mock_get, mock_post, monkeypatch):
    # Raise generic Exception (e.g., in get_role_policies) to hit lines 167-169
    monkeypatch.setattr(mr, "ROLE_IDS", "['rid']", raising=False)
    monkeypatch.setattr(mr, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mr, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mr, "TARGET_ENV_URL", "https://t")

    role_resp = MagicMock()
    role_resp.raise_for_status.return_value = None
    role_resp.json.return_value = {
        "role": {"definition": {"name": "Custom", "permissions": ["policies.read"]}}
    }
    mock_get.side_effect = [role_resp]

    create_post = MagicMock()
    create_post.raise_for_status.return_value = None
    create_post.json.return_value = {"ID": "new-role"}
    mock_post.return_value = create_post

    monkeypatch.setattr(
        mr, "get_role_policies", lambda _id: (_ for _ in ()).throw(Exception("oops"))
    )
    with pytest.raises(Exception):
        mr.main()


def test_run_as_script(monkeypatch):
    # Cover line 172
    import runpy, requests as _requests

    monkeypatch.setenv("ROLE_IDS", "[]")
    monkeypatch.setenv("TARGET_VAULT_ID", "tv")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://s")
    monkeypatch.setenv("TARGET_ENV_URL", "https://t")
    with patch.object(_requests, "get") as g, patch.object(_requests, "post") as p:
        runpy.run_module("migrate_roles", run_name="__main__")
        # ROLE_IDS is [] so no network calls expected
        assert g.call_count == 0
        assert p.call_count == 0
