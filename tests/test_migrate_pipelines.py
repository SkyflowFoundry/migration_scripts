import importlib
import sys
from types import SimpleNamespace

import dotenv
import pytest


BASE_ENV = {
    "PIPELINE_ID": "pipeline-from-env",
    "SOURCE_VAULT_ID": "source-vault",
    "TARGET_VAULT_ID": "target-vault",
    "SOURCE_ACCOUNT_ID": "account-source",
    "TARGET_ACCOUNT_ID": "account-target",
    "SOURCE_ACCOUNT_AUTH": "token-source",
    "TARGET_ACCOUNT_AUTH": "token-target",
    "SOURCE_ENV_URL": "https://source.example.com",
    "TARGET_ENV_URL": "https://target.example.com",
    "SOURCE_DATASTORE_CONFIG": "",
    "TARGET_DATASTORE_CONFIG": "",
}


def load_module(monkeypatch, **env_overrides):
    complete_env = {**BASE_ENV, **env_overrides}
    for key, value in complete_env.items():
        monkeypatch.setenv(key, value)
    if "migrate_pipelines" in sys.modules:
        del sys.modules["migrate_pipelines"]
    return importlib.import_module("migrate_pipelines")


def test_strip_empty_values(monkeypatch):
    module = load_module(monkeypatch)
    source = {"a": "", "b": None, "c": {"d": "value", "e": ""}, "f": [1, "", None]}
    assert module.strip_empty_values(source) == {"c": {"d": "value"}, "f": [1]}


def test_validate_ftp_server_success(monkeypatch):
    module = load_module(monkeypatch)
    config = {
        "transferProtocol": "SFTP",
        "plainText": {
            "hostname": "host",
            "port": "",
            "username": "user",
            "password": "",
            "sshKeyID": "key",
        },
        "encrypted": {"encryptedCredentials": "cipher"},
        "skyflowHosted": False,
        "extra": "ignored",
    }
    result = module.validate_ftp_server(config, "source")
    assert result == {
        "transferProtocol": "SFTP",
        "plainText": {
            "hostname": "host",
            "username": "user",
            "sshKeyID": "key",
        },
        "encrypted": {"encryptedCredentials": "cipher"},
        "skyflowHosted": False,
    }


@pytest.mark.parametrize(
    "config, expected_message",
    [
        ("not-a-dict", "ftpServer must be an object"),
        ({"plainText": "oops"}, "ftpServer.plainText must be an object"),
        ({"extra": "value"}, "must include non-empty credentials"),
        ({"transferProtocol": "SFTP", "encrypted": "oops"}, "ftpServer.encrypted must be an object"),
        ({"plainText": {}}, "transferProtocol is required"),
        ({"transferProtocol": "SFTP"}, "plainText or encrypted credentials"),
    ],
)
def test_validate_ftp_server_errors(monkeypatch, config, expected_message):
    module = load_module(monkeypatch)
    with pytest.raises(ValueError, match=expected_message):
        module.validate_ftp_server(config, "source")


def test_validate_s3_bucket_success(monkeypatch):
    module = load_module(monkeypatch)
    config = {
        "name": "bucket",
        "region": "us-west-2",
        "assumedRoleARN": "arn:aws:iam::role/example",
        "ignored": "value",
    }
    assert module.validate_s3_bucket(config, "target") == {
        "name": "bucket",
        "region": "us-west-2",
        "assumedRoleARN": "arn:aws:iam::role/example",
    }


@pytest.mark.parametrize(
    "config, expected_message",
    [
        ("not-a-dict", "s3Bucket must be an object"),
        ({}, "must include non-empty configuration"),
        ({"name": "bucket", "region": "us-west-2"}, "missing required fields"),
    ],
)
def test_validate_s3_bucket_errors(monkeypatch, config, expected_message):
    module = load_module(monkeypatch)
    with pytest.raises(ValueError, match=expected_message):
        module.validate_s3_bucket(config, "target")


def test_load_datastore_input_variants(monkeypatch):
    module = load_module(monkeypatch)
    assert module.load_datastore_input("", "source") is None
    assert module.load_datastore_input(None, "source") is None

    with pytest.raises(ValueError, match="Invalid JSON"):
        module.load_datastore_input("{invalid}", "source")
    with pytest.raises(ValueError, match="must be a JSON object"):
        module.load_datastore_input("[]", "source")
    with pytest.raises(ValueError, match="exactly one"):
        module.load_datastore_input(
            '{"ftpServer": {}, "s3Bucket": {}}', "source"
        )

    ftp_override = module.load_datastore_input(
        '{"ftpServer": {"transferProtocol": "FTPS", "plainText": {"hostname": "h", "username": "u"}}}',
        "source",
    )
    assert ftp_override == {
        "ftpServer": {
            "transferProtocol": "FTPS",
            "plainText": {"hostname": "h", "username": "u"},
        }
    }

    s3_override = module.load_datastore_input(
        '{"s3Bucket": {"name": "bucket", "region": "us", "assumedRoleARN": "arn"}}', "target"
    )
    assert s3_override == {
        "s3Bucket": {"name": "bucket", "region": "us", "assumedRoleARN": "arn"}
    }


def test_replace_datastore_input_replaces_only_datastore(monkeypatch):
    module = load_module(monkeypatch)
    existing = {
        "dataFormat": "CSV",
        "ftpServer": {"transferProtocol": "FTPS"},
        "other": "value",
    }
    override = {"ftpServer": {"transferProtocol": "SFTP"}}
    result = module.replace_datastore_input(existing, override)
    assert result == {
        "dataFormat": "CSV",
        "other": "value",
        "ftpServer": {"transferProtocol": "SFTP"},
    }
    assert existing["ftpServer"]["transferProtocol"] == "FTPS"


def test_replace_datastore_input_fails_on_ftp_to_s3(monkeypatch):
    module = load_module(monkeypatch)
    existing = {
        "dataFormat": "CSV",
        "ftpServer": {"transferProtocol": "FTPS"},
    }
    override = {"s3Bucket": {"name": "bucket"}}
    with pytest.raises(ValueError, match="Cannot override FTP datastore"):
        module.replace_datastore_input(existing, override)


def test_replace_datastore_input_fails_on_s3_to_ftp(monkeypatch):
    module = load_module(monkeypatch)
    existing = {
        "dataFormat": "CSV",
        "s3Bucket": {"name": "bucket", "region": "us", "assumedRoleARN": "arn"},
    }
    override = {"ftpServer": {"transferProtocol": "SFTP", "plainText": {"hostname": "h", "username": "u"}}}
    with pytest.raises(ValueError, match="Cannot override S3 datastore"):
        module.replace_datastore_input(existing, override)


def test_transform_pipeline_payload(monkeypatch):
    module = load_module(monkeypatch)
    pipeline = {
        "vaultID": "original-vault",
        "source": {"ftpServer": {"transferProtocol": "FTPS"}},
        "destination": {"s3Bucket": {"name": "existing"}},
    }
    source_override = {"ftpServer": {"transferProtocol": "SFTP"}}
    target_override = {"s3Bucket": {"name": "new", "region": "us-east-1"}}

    result = module.transform_pipeline_payload(
        pipeline,
        source_datastore_input=source_override,
        target_datastore_input=target_override,
    )

    assert result["vaultID"] == BASE_ENV["TARGET_VAULT_ID"]
    assert result["source"]["ftpServer"] == {"transferProtocol": "SFTP"}
    assert result["destination"]["s3Bucket"] == {
        "name": "new",
        "region": "us-east-1",
    }
    # Ensure original object is untouched
    assert pipeline["source"]["ftpServer"]["transferProtocol"] == "FTPS"


def test_list_pipelines(monkeypatch):
    module = load_module(monkeypatch)
    calls = {}

    def fake_get(url, headers):
        calls["url"] = url
        calls["headers"] = headers
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"pipelines": [{"ID": "pipeline-1"}]},
        )

    monkeypatch.setattr(module.requests, "get", fake_get)
    result = module.list_pipelines("vault-123")
    assert result == [{"ID": "pipeline-1"}]
    assert calls["url"].endswith("vaultID=vault-123")
    assert calls["headers"]["Authorization"].startswith("Bearer")


def test_get_pipeline(monkeypatch):
    module = load_module(monkeypatch)
    captured = {}

    def fake_get(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"pipeline":{"ID": "pipeline-1", "name": "Example"}},
        )

    monkeypatch.setattr(module.requests, "get", fake_get)
    pipeline = module.get_pipeline("pipeline-1")
    assert pipeline["name"] == "Example"
    assert captured["url"].endswith("/pipeline-1")


def test_create_pipeline(monkeypatch):
    module = load_module(monkeypatch)
    captured = {}

    def fake_post(url, json, headers):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers

        class DummyResponse:
            status_code = 200

            def raise_for_status(self):
                return None

        return DummyResponse()

    monkeypatch.setattr(module.requests, "post", fake_post)
    payload = {"name": "new-pipeline"}
    response = module.create_pipeline(payload)
    assert response.status_code == 200
    assert captured["json"] == payload
    assert captured["url"].endswith("/v1/pipelines")


def test_main_success(monkeypatch, capsys):
    source_config = """
    {
        "ftpServer": {
            "transferProtocol": "FTPS",
            "plainText": {"hostname": "host", "username": "user"}
        }
    }
    """
    target_config = """
    {
        "s3Bucket": {
            "name": "bucket",
            "region": "us-west-2",
            "assumedRoleARN" : "test"
        }
    }
    """
    module = load_module(
        monkeypatch,
        SOURCE_DATASTORE_CONFIG=source_config,
        TARGET_DATASTORE_CONFIG=target_config,
    )

    pipeline = {
        "ID": "pipeline-1",
        "name": "Sample Pipeline",
        "vaultID": "old-vault",
        "source": {"ftpServer": {"transferProtocol": "SFTP"}},
        "destination": {"s3Bucket": {"name": "old"}},
    }
    monkeypatch.setattr(module, "get_pipeline", lambda pipeline_id: pipeline)

    captured_payload = {}

    class SuccessResponse:
        status_code = 200

        def json(self):
            return {"ID": "new-id"}

    def fake_create_pipeline(payload):
        captured_payload.update(payload)
        return SuccessResponse()

    monkeypatch.setattr(module, "create_pipeline", fake_create_pipeline)
    module.main("pipeline-1")
    stdout = capsys.readouterr().out
    assert "Pipeline migrated successfully" in stdout
    assert captured_payload["vaultID"] == BASE_ENV["TARGET_VAULT_ID"]
    assert "ftpServer" in captured_payload["source"]
    assert "s3Bucket" in captured_payload["destination"]


def test_main_failure(monkeypatch, capsys):
    module = load_module(monkeypatch)
    pipeline = {"ID": "pipeline-2", "name": "Failing Pipeline"}
    monkeypatch.setattr(module, "get_pipeline", lambda pipeline_id: pipeline)

    class FailureResponse:
        status_code = 500
        content = b"problem"

    monkeypatch.setattr(module, "create_pipeline", lambda payload: FailureResponse())
    module.main("pipeline-2")
    stdout = capsys.readouterr().out
    assert "Pipeline migration failed" in stdout


def test_main_http_error_branch(monkeypatch, capsys):
    import requests

    module = load_module(monkeypatch)

    class Resp:
        content = b"http boom"

    http_err = requests.exceptions.HTTPError(response=Resp())

    def raise_http_error(_):
        raise http_err

    monkeypatch.setattr(module, "get_pipeline", raise_http_error)

    with pytest.raises(requests.exceptions.HTTPError):
        module.main("pipeline-http-error")

    stdout = capsys.readouterr().out
    assert "HTTP error" in stdout


def test_main_other_exception_branch(monkeypatch, capsys):
    module = load_module(monkeypatch)
    pipeline = {"ID": "pipeline-3", "name": "Other Error"}
    monkeypatch.setattr(module, "get_pipeline", lambda pipeline_id: pipeline)

    def boom(_payload):
        raise RuntimeError("explode")

    monkeypatch.setattr(module, "create_pipeline", boom)

    with pytest.raises(RuntimeError):
        module.main("pipeline-other-error")

    stdout = capsys.readouterr().out
    assert "other error" in stdout


def test_run_as_script_requires_pipeline_id(monkeypatch):
    import runpy
    import sys
    import dotenv

    if "migrate_pipelines" in sys.modules:
        del sys.modules["migrate_pipelines"]

    for key, value in BASE_ENV.items():
        if key != "PIPELINE_ID":
            monkeypatch.setenv(key, value)
    monkeypatch.setenv("PIPELINE_ID", "")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="PIPELINE_ID is required"):
        runpy.run_module("migrate_pipelines", run_name="__main__")


def test_run_as_script_executes_main(monkeypatch):
    import runpy
    import requests

    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)

    captured = {}

    class FakeGetResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "pipeline": {
                    "ID": BASE_ENV["PIPELINE_ID"],
                    "name": "Script Pipeline",
                    "vaultID": "source-vault",
                    "source": {},
                    "destination": {},
                }
            }

    class FakePostResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ID": "new-pipeline"}

    def fake_get(url, headers):
        captured["get_url"] = url
        return FakeGetResponse()

    def fake_post(url, json, headers):
        captured["post_url"] = url
        captured["payload"] = json
        return FakePostResponse()

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    runpy.run_module("migrate_pipelines", run_name="__main__")

    assert captured["post_url"].endswith("/v1/pipelines")
    assert captured["payload"]["vaultID"] == BASE_ENV["TARGET_VAULT_ID"]
