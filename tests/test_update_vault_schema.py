import pytest
from unittest.mock import MagicMock, patch

import update_vault_schema as uvs


@patch("update_vault_schema.requests.patch")
@patch("update_vault_schema.requests.get")
def test_main_success(mock_get, mock_patch, monkeypatch):
    monkeypatch.setattr(uvs, "SOURCE_VAULT_ID", "sv", raising=False)
    monkeypatch.setattr(uvs, "TARGET_VAULT_ID", "tv", raising=False)
    monkeypatch.setattr(uvs, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(uvs, "TARGET_ENV_URL", "https://t")

    g = MagicMock()
    g.raise_for_status.return_value = None
    g.json.return_value = {"vault": {"name": "V", "description": "D", "schemas": [], "tags": []}}
    mock_get.return_value = g

    p = MagicMock(); p.raise_for_status.return_value = None; p.json.return_value = {"ID": "tv"}
    mock_patch.return_value = p

    uvs.main()
    assert mock_patch.called


def test_main_missing_ids(monkeypatch):
    monkeypatch.setattr(uvs, "SOURCE_VAULT_ID", None, raising=False)
    monkeypatch.setattr(uvs, "TARGET_VAULT_ID", None, raising=False)
    # Should early-return without making any network calls
    with patch("update_vault_schema.requests.get") as g, patch("update_vault_schema.requests.patch") as p:
        result = uvs.main()
        assert result is None
        assert g.call_count == 0
        assert p.call_count == 0


def test_main_http_error(monkeypatch):
    import requests

    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    monkeypatch.setattr(uvs, "SOURCE_VAULT_ID", "sv", raising=False)
    monkeypatch.setattr(uvs, "TARGET_VAULT_ID", "tv", raising=False)
    monkeypatch.setattr(uvs, "get_vault_details", lambda _id: (_ for _ in ()).throw(err))

    with pytest.raises(SystemExit):
        uvs.main()


def test_main_generic_exception(monkeypatch):
    # Cause a generic exception after fetch to cover lines 61-63
    monkeypatch.setattr(uvs, "SOURCE_VAULT_ID", "sv", raising=False)
    monkeypatch.setattr(uvs, "TARGET_VAULT_ID", "tv", raising=False)
    monkeypatch.setattr(uvs, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(uvs, "TARGET_ENV_URL", "https://t")
    g = MagicMock()
    g.raise_for_status.return_value = None
    g.json.return_value = {"vault": {"name": "V", "description": "D", "schemas": [], "tags": []}}
    with patch("update_vault_schema.requests.get", return_value=g):
        with patch("update_vault_schema.update_vault", side_effect=Exception("boom")):
            with pytest.raises(SystemExit):
                uvs.main()


def test_run_as_script(monkeypatch):
    # Cover __main__ guard (line 66)
    import runpy, requests as _requests
    monkeypatch.setenv("SOURCE_VAULT_ID", "sv")
    monkeypatch.setenv("TARGET_VAULT_ID", "tv")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://s")
    monkeypatch.setenv("TARGET_ENV_URL", "https://t")
    g = MagicMock(); g.raise_for_status.return_value = None; g.json.return_value = {"vault": {"name": "V", "description": "D", "schemas": [], "tags": []}}
    p = MagicMock(); p.raise_for_status.return_value = None; p.json.return_value = {"ID": "tv"}
    with patch.object(_requests, "get", return_value=g) as mget, patch.object(_requests, "patch", return_value=p) as mpatch:
        runpy.run_module("update_vault_schema", run_name="__main__")
        assert mget.call_count == 1
        assert mpatch.call_count == 1
