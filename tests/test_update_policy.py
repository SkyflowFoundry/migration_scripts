import update_policy as up


def test_transform_policy_payload_handles_update_and_new_rules(monkeypatch):
    target = {
        "policy": {
            "ID": "tp",
            "name": "t",
            "displayName": "td",
            "description": "tdesc",
            "resource": {"ID": "tv"},
            "rules": [
                {"ID": "r1", "name": "R1", "ruleExpression": "eq"},
                {"ID": "r2", "name": "R2", "ruleExpression": "old"},
            ],
        }
    }
    source = {
        "policy": {
            "ID": "sp",
            "name": "s",
            "displayName": "sd",
            "description": "sdesc",
            "rules": [
                {
                    "ID": "sr1",
                    "name": "R1",
                    "ruleExpression": "eq",  # same as target -> skipped
                    "actions": ["POLICY.read"],
                    "resources": ["vault:v/table:t/column:c"],
                    "resourceType": "COLUMN",
                    "dlpFormat": None,
                },
                {
                    "ID": "sr2",
                    "name": "R2",
                    "ruleExpression": "new-exp",  # update existing r2
                    "actions": ["POLICY.write"],
                    "resources": ["vault:v/table:orders"],
                    "resourceType": "TABLE",
                    "dlpFormat": None,
                },
                {
                    "ID": "sr3",
                    "name": "R3",
                    "ruleExpression": "extra",  # new rule
                    "actions": ["POLICY.read"],
                    "resources": ["columngroup:cg1"],
                    "resourceType": "COLUMN_GROUP",
                    "dlpFormat": None,
                },
            ],
        }
    }
    payload = up.transform_policy_payload(source, target)
    assert payload["policy"]["ID"] == "tp"
    # First rule skipped, so only 2 ruleParams remain
    assert len(payload["ruleParams"]) == 2
    # Check structure for one
    names = {r["name"] for r in payload["ruleParams"]}
    assert names == {"R2", "R3"}
