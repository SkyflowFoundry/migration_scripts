import pytest
import requests
from unittest.mock import MagicMock, patch

import migrate_policies as mp


def test_transform_policy_payload_builds_rule_params(monkeypatch):
    monkeypatch.setattr(mp, "TARGET_VAULT_ID", "tv")
    source = {
        "policy": {
            "ID": "pid",
            "namespace": "ns",
            "status": "ACTIVE",
            "BasicAudit": {},
            "members": [],
            "rules": [
                {
                    "ID": "r1",
                    "name": "R1",
                    "ruleExpression": "x > 1",
                    "actions": ["POLICY.read", "POLICY.write"],
                    "resources": [
                        "vault:vid/table:users/column:email",
                        "vault:vid/table:users/column:ssn",
                    ],
                    "resourceType": "COLUMN",
                    "dlpFormat": None,
                },
                {
                    "ID": "r2",
                    "name": "R2",
                    "ruleExpression": "y == 2",
                    "actions": ["POLICY.read"],
                    "resources": ["vault:vid/table:orders"],
                    "resourceType": "TABLE",
                    "dlpFormat": None,
                },
                {
                    "ID": "r3",
                    "name": "R3",
                    "ruleExpression": "true",
                    "actions": ["POLICY.read"],
                    "resources": ["columngroup:pii"],
                    "resourceType": "COLUMN_GROUP",
                    "dlpFormat": None,
                },
            ],
        }
    }
    out = mp.transform_policy_payload(source)
    assert out["resource"] == {"ID": "tv", "type": "VAULT"}
    assert out["activated"] is True
    assert "rules" not in out
    assert len(out["ruleParams"]) == 3
    # Validate one conversion
    col_rule = out["ruleParams"][0]
    assert "columnRuleParams" in col_rule and col_rule["columnRuleParams"]["columns"][0].endswith("users.email")


@patch("migrate_policies.requests.post")
@patch("migrate_policies.requests.get")
def test_main_creates_policies(mock_get, mock_post, monkeypatch):
    monkeypatch.setattr(mp, "TARGET_VAULT_ID", "tv")
    monkeypatch.setattr(mp, "SOURCE_ENV_URL", "https://s")
    monkeypatch.setattr(mp, "TARGET_ENV_URL", "https://t")

    g = MagicMock()
    g.raise_for_status.return_value = None
    g.json.return_value = {
        "policy": {
            "ID": "p1",
            "namespace": "ns",
            "status": "ACTIVE",
            "BasicAudit": {},
            "members": [],
            "rules": [
                {
                    "ID": "r",
                    "name": "R",
                    "ruleExpression": "x",
                    "actions": ["POLICY.read"],
                    "resources": ["vault:v/table:users/column:email"],
                    "resourceType": "COLUMN",
                    "dlpFormat": None,
                }
            ],
        }
    }
    mock_get.return_value = g

    p = MagicMock()
    p.raise_for_status.return_value = None
    p.json.return_value = {"ID": "newp"}
    mock_post.return_value = p

    created = mp.main(policy_ids=["p1"])
    assert isinstance(created, list) and created


def test_main_http_error(monkeypatch):
    class Resp:
        content = b"boom"

    err = requests.exceptions.HTTPError(response=Resp())

    def raise_err(_):
        raise err

    monkeypatch.setattr(mp, "get_policy", raise_err)
    with pytest.raises(requests.exceptions.HTTPError):
        mp.main(policy_ids=["p1"])


def test_main_generic_exception(monkeypatch):
    # Cause transform to fail with KeyError to hit generic except (111-113)
    monkeypatch.setattr(mp, "transform_policy_payload", lambda _: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(Exception):
        mp.main(policy_ids=["p1"])


def test_run_as_script(monkeypatch):
    # Run as __main__ to cover line 117
    import runpy
    import requests as _requests

    monkeypatch.setenv("POLICY_IDS", "['p1']")
    monkeypatch.setenv("TARGET_VAULT_ID", "tv")
    monkeypatch.setenv("SOURCE_ENV_URL", "https://s")
    monkeypatch.setenv("TARGET_ENV_URL", "https://t")

    src = MagicMock(); src.raise_for_status.return_value = None; src.json.return_value = {"policy": {"ID": "p1", "namespace": "n", "status": "A", "BasicAudit": {}, "members": [], "rules": [{"ID": "r", "name": "R", "ruleExpression": "x", "actions": ["POLICY.read"], "resources": ["vault:v/table:t/column:c"], "resourceType": "COLUMN", "dlpFormat": None}]}}
    tgt = MagicMock(); tgt.raise_for_status.return_value = None; tgt.json.return_value = {"ID": "np"}

    with patch.object(_requests, "get", return_value=src) as mget, patch.object(_requests, "post", return_value=tgt) as mpost:
        runpy.run_module("migrate_policies", run_name="__main__")
        assert mget.call_count >= 1
        assert mpost.call_count >= 1
