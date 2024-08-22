import os
import ast
import requests

from dotenv import load_dotenv
load_dotenv()

POLICY_IDS = os.getenv("POLICY_IDS")
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")
SOURCE_VAULT_ACCOUNT_ID = os.getenv("SOURCE_VAULT_ACCOUNT_ID")
TARGET_VAULT_ACCOUNT_ID = os.getenv("TARGET_VAULT_ACCOUNT_ID")
SOURCE_VAULT_AUTH = os.getenv("SOURCE_VAULT_AUTH")
TARGET_VAULT_AUTH = os.getenv("TARGET_VAULT_AUTH")
SOURCE_VAULT_ENV_URL = os.getenv("SOURCE_VAULT_ENV_URL")
TARGET_VAULT_ENV_URL = os.getenv("TARGET_VAULT_ENV_URL")

SOURCE_VAULT_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": SOURCE_VAULT_ACCOUNT_ID,
    "Authorization": f"Bearer {SOURCE_VAULT_AUTH}",
    "Content-Type": "application/json",
}

TARGET_VAULT_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": TARGET_VAULT_ACCOUNT_ID,
    "Authorization": f"Bearer {TARGET_VAULT_AUTH}",
    "Content-Type": "application/json",
}


def get_policy(policy_id):
    response = requests.get(
        f"{SOURCE_VAULT_ENV_URL}/v1/policies/{policy_id}", headers=SOURCE_VAULT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def create_policy(policy_data):
    response = requests.post(
        f"{TARGET_VAULT_ENV_URL}/v1/policies", json=policy_data, headers=TARGET_VAULT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def transform_policy_payload(source_resource):
    transformed_resource = source_resource["policy"]
    transformed_resource["resource"] = {"ID": TARGET_VAULT_ID, "type": "VAULT"}
    policy_rules = transformed_resource["rules"]
    policy_rule_params = []

    for policy_rule in policy_rules:
        temp_rule_param = {"name": policy_rule["name"], "ruleExpression": policy_rule["ruleExpression"]}
        ruleParams = policy_rule
        actions: list[str] = ruleParams["actions"]
        rule_param_actions = [action.split(".")[1].upper() for action in actions]
        resources: list[str] = ruleParams["resources"]
        resourceType = policy_rule["resourceType"]

        ruleParams["vaultID"] = TARGET_VAULT_ID
        ruleParams["actions"] = rule_param_actions
        ruleParams["action"] = rule_param_actions[0]

        del ruleParams["ID"]
        del ruleParams["resources"]
        del ruleParams["dlpFormat"]
        del ruleParams["resourceType"]
        del ruleParams["ruleExpression"]

        if resourceType == "COLUMN":
            ruleParams["columns"] = [
                f"{resource.split('/')[1].split(':')[1]}.{resource.split('/')[2].split(':')[1]}"
                for resource in resources
            ]
            temp_rule_param["columnRuleParams"] = ruleParams
        elif resourceType == "TABLE":
            ruleParams["tableName"] = resources[0].split("table:")[1]
            temp_rule_param["tableRuleParams"] = ruleParams
        elif resourceType == "COLUMN_GROUP":
            ruleParams["columnGroups"] = [
                resource.split("columngroup:")[1] for resource in resources
            ]
            temp_rule_param["columnGroupRuleParams"] = ruleParams
        policy_rule_params.append(temp_rule_param)

    transformed_resource["ruleParams"] = policy_rule_params
    transformed_resource["activated"] = True

    del transformed_resource["ID"]
    del transformed_resource["namespace"]
    del transformed_resource["status"]
    del transformed_resource["BasicAudit"]
    del transformed_resource["members"]
    del transformed_resource["rules"]

    return transformed_resource


def main(policy_ids=None):
    try:
        policy_ids = policy_ids if policy_ids else ast.literal_eval(POLICY_IDS)
        policies_created = []
        for policy_id in policy_ids:
            fetched_policy = get_policy(policy_id)
            policy_payload = transform_policy_payload(fetched_policy)
            policy = create_policy(policy_payload)
            policies_created.append(policy)
        print(f"-- POLICIES Migration done --")        
        return policies_created
    except requests.exceptions.HTTPError as http_err:
        print(f'-- migrate_policies HTTP error: {http_err.response.content.decode()} --')
        raise http_err
    except Exception as err:
        print(f"-- migrate_policies error: {err} --")
        raise err


if __name__ == "__main__":
    main()
