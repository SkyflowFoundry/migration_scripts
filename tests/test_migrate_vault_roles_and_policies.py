import pytest
import requests
from unittest.mock import MagicMock, patch

import migrate_vault_roles_and_policies as mvrp


@patch("migrate_vault_roles_and_policies.migrate_roles")
@patch("migrate_vault_roles_and_policies.requests.get")
def test_main_success(mock_get, mock_migrate_roles, monkeypatch):
    monkeypatch.setattr(mvrp, "SOURCE_VAULT_ID", "sv", raising=False)
    monkeypatch.setattr(mvrp, "SOURCE_ENV_URL", "https://s")
    roles_resp = MagicMock(); roles_resp.raise_for_status.return_value = None; roles_resp.json.return_value = {"roles": [{"ID": "r1"}, {"ID": "r2"}]}
    mock_get.return_value = roles_resp

    mvrp.main()
    assert mock_migrate_roles.called


def test_main_http_error(monkeypatch):
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())
    def raise_err():
        raise err

    monkeypatch.setattr(mvrp, "list_all_vault_custom_roles", raise_err)
    # Function calls exit(1) on HTTPError; can't catch with pytest.raises directly.
    # Instead ensure it doesn't raise unhandled exceptions by intercepting SystemExit.
    with pytest.raises(SystemExit):
        mvrp.main()


def test_main_generic_exception(monkeypatch):
    # Cause a non-HTTP exception and ensure SystemExit (lines 46-48)
    monkeypatch.setattr(mvrp, "list_all_vault_custom_roles", lambda: (_ for _ in ()).throw(ValueError("x")))
    with pytest.raises(SystemExit):
        mvrp.main()


def test_run_as_script(monkeypatch):
    # Run module as script to cover line 52
    import runpy, requests as _requests, types, sys
    monkeypatch.setenv("SOURCE_VAULT_ID", "sv")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://s")
    # Dummy migrate_roles.main to avoid side effects and assert it was called
    dummy_main = MagicMock()
    dummy = types.SimpleNamespace(main=dummy_main)
    sys.modules["migrate_roles"] = dummy

    r = MagicMock(); r.raise_for_status.return_value = None; r.json.return_value = {"roles": []}
    with patch.object(_requests, "get", return_value=r) as mget:
        runpy.run_module("migrate_vault_roles_and_policies", run_name="__main__")
        # Should fetch once and call migrate_roles with an empty list
        assert mget.call_count == 1
        assert dummy_main.called
        args, _ = dummy_main.call_args
        assert args == ([],)
