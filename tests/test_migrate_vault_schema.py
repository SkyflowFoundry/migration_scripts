from unittest.mock import MagicMock, patch, mock_open
import pytest
import migrate_vault_schema as mvs


def test_transform_payload_uses_env_overrides(monkeypatch):
    monkeypatch.setattr(mvs, "WORKSPACE_ID", "ws1")
    monkeypatch.setattr(mvs, "VAULT_NAME", "MyVault")
    monkeypatch.setattr(mvs, "VAULT_DESCRIPTION", "Desc")
    monkeypatch.setattr(mvs, "VAULT_SCHEMA_CONFIG", None)
    vault_details = {"name": "SName", "description": "SDesc", "schemas": [], "tags": []}
    out = mvs.transform_payload(vault_details)
    assert out["name"] == "MyVault"
    assert out["description"] == "Desc"
    assert out["workspaceID"] == "ws1"


@patch("migrate_vault_schema.requests.post")
@patch("migrate_vault_schema.requests.get")
def test_main_fetches_vault_and_creates(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(mvs, "SOURCE_VAULT_ID", "sv")
    monkeypatch.setattr(mvs, "WORKSPACE_ID", "ws1")
    monkeypatch.setattr(mvs, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mvs, "TARGET_ENV_URL", "https://t")
    monkeypatch.delenv("MIGRATE_GOVERNANCE", raising=False)

    g = MagicMock()
    g.raise_for_status.return_value = None
    g.json.return_value = {
        "vault": {"name": "V", "description": "D", "schemas": [], "tags": []}
    }
    mock_get.return_value = g

    p = MagicMock()
    p.raise_for_status.return_value = None
    p.json.return_value = {"ID": "new-v"}
    mock_post.return_value = p

    mvs.main()
    assert mock_get.called and mock_post.called


@patch("migrate_vault_schema.requests.post")
def test_main_with_config_and_migrate_governance(mock_post, monkeypatch, tmp_path):
    monkeypatch.setattr(mvs, "VAULT_SCHEMA_CONFIG", "config_file", raising=False)
    monkeypatch.setattr(mvs, "WORKSPACE_ID", "ws1", raising=False)
    monkeypatch.setattr(mvs, "TARGET_ENV_URL", "https://t")

    p = MagicMock()
    p.raise_for_status.return_value = None
    p.json.return_value = {"ID": "v1"}
    mock_post.return_value = p

    # Set up MIGRATE_GOVERNANCE env var and env file path
    monkeypatch.setenv("MIGRATE_GOVERNANCE", "1")
    env_file = tmp_path / "env"
    monkeypatch.setenv("GITHUB_ENV", str(env_file))

    schema_json = '{"schemas": [], "tags": []}'
    # Use a single open mock; we'll assert the append call targeting env file is made
    with patch("builtins.open", mock_open(read_data=schema_json)) as mopen:
        mvs.main()
        # Check that the env file was opened for append
        called_paths = [call.args[0] for call in mopen.mock_calls if call[0] == ""]
        # The second open call should be for env_file path
        assert any(str(env_file) in str(arg) for arg in called_paths)


def test_missing_inputs_and_workspace(monkeypatch):
    monkeypatch.setattr(mvs, "VAULT_SCHEMA_CONFIG", None, raising=False)
    monkeypatch.setattr(mvs, "SOURCE_VAULT_ID", None, raising=False)
    monkeypatch.setattr(mvs, "WORKSPACE_ID", None, raising=False)
    # Should early-return without making any network calls
    with patch("migrate_vault_schema.requests.get") as g, patch(
        "migrate_vault_schema.requests.post"
    ) as p:
        result = mvs.main()
        assert result is None
        assert g.call_count == 0
        assert p.call_count == 0


def test_http_error_branch(monkeypatch):
    import requests

    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())
    monkeypatch.setattr(mvs, "SOURCE_VAULT_ID", "sv", raising=False)
    monkeypatch.setattr(mvs, "WORKSPACE_ID", "ws1", raising=False)
    monkeypatch.setattr(
        mvs, "get_vault_details", lambda _id: (_ for _ in ()).throw(err)
    )
    with pytest.raises(SystemExit):
        mvs.main()
    assert SystemExit


def test_generic_exception_branch(monkeypatch):
    # Cause generic exception during create (lines 84-86)
    monkeypatch.setattr(mvs, "VAULT_SCHEMA_CONFIG", "config_file", raising=False)
    monkeypatch.setattr(mvs, "WORKSPACE_ID", "ws1", raising=False)
    schema_json = '{"schemas": [], "tags": []}'
    with patch("builtins.open", mock_open(read_data=schema_json)):
        monkeypatch.setattr(
            mvs, "create_vault", lambda payload: (_ for _ in ()).throw(Exception("x"))
        )
        with pytest.raises(SystemExit):
            mvs.main()
        assert SystemExit


def test_run_as_script(monkeypatch):
    # Run as script to cover line 89
    import runpy, requests as _requests

    monkeypatch.setenv("VAULT_SCHEMA_CONFIG", "config_file")
    monkeypatch.setenv("WORKSPACE_ID", "ws1")
    monkeypatch.setenv("TARGET_ENV_URL", "https://t")
    schema_json = '{"schemas": [], "tags": []}'
    with patch("builtins.open", mock_open(read_data=schema_json)):
        p = MagicMock()
        p.raise_for_status.return_value = None
        p.json.return_value = {"ID": "v1"}
        with patch.object(_requests, "post", return_value=p) as mpost:
            runpy.run_module("migrate_vault_schema", run_name="__main__")
            assert mpost.call_count == 1
