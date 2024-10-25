import os
import requests

SOURCE_POLICY_ID = os.getenv("SOURCE_POLICY_ID")
TARGET_POLICY_ID = os.getenv("TARGET_POLICY_ID")
SOURCE_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
TARGET_ACCOUNT_ID = os.getenv("TARGET_ACCOUNT_ID")
SOURCE_ACCOUNT_AUTH = os.getenv("SOURCE_ACCOUNT_AUTH")
TARGET_ACCOUNT_AUTH = os.getenv("TARGET_ACCOUNT_AUTH")
SOURCE_ENV_URL = os.getenv("SOURCE_ENV_URL")
TARGET_ENV_URL = os.getenv("TARGET_ENV_URL")

SOURCE_ACCOUNT_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": SOURCE_ACCOUNT_ID,
    "Authorization": f"Bearer {SOURCE_ACCOUNT_AUTH}",
    "Content-Type": "application/json",
}

TARGET_ACCOUNT_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": TARGET_ACCOUNT_ID,
    "Authorization": f"Bearer {TARGET_ACCOUNT_AUTH}",
    "Content-Type": "application/json",
}


def get_source_policy(policy_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/policies/{policy_id}", headers=SOURCE_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_target_policy(policy_id):
    response = requests.get(
        f"{TARGET_ENV_URL}/v1/policies/{policy_id}", headers=TARGET_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def update_policy(policy_data):
    response = requests.patch(
        f"{TARGET_ENV_URL}/v1/policies/{TARGET_POLICY_ID}",
        json=policy_data,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def transform_policy_payload(source_policy, target_policy):
    target_resource = target_policy["policy"]
    source_resource = source_policy["policy"]

    update_payload = {
        "policy": {
            "ID": target_resource["ID"],
            "name": source_resource["name"],
            "displayName": source_resource["displayName"],
            "description": source_resource["description"],
        }
    }

    source_policy_rules = source_resource["rules"]
    target_policy_rules = target_resource["rules"]
    target_vault_id = target_resource["resource"]["ID"]
    target_policy_rule_params = []
    no_of_source_policy_rules = len(source_policy_rules)
    no_of_target_policy_rules = len(target_policy_rules)
    for i in range(no_of_source_policy_rules):
        source_policy_rule = source_policy_rules[i]
        if i < no_of_target_policy_rules:
            target_policy_rule = target_policy_rules[i]
            if (
                source_policy_rule["ruleExpression"]
                == target_policy_rule["ruleExpression"]
            ):
                continue
            else:
                temp_rule_param = {
                    "ID": target_policy_rule["ID"],
                    "name": source_policy_rule["name"],
                    "ruleExpression": source_policy_rule["ruleExpression"],
                }
                ruleParams = source_policy_rule
                actions: list[str] = ruleParams["actions"]
                rule_param_actions = [
                    action.split(".")[1].upper() for action in actions
                ]
                resources: list[str] = ruleParams["resources"]
                resourceType = source_policy_rule["resourceType"]

                ruleParams["vaultID"] = target_vault_id
                ruleParams["actions"] = rule_param_actions
                ruleParams["action"] = rule_param_actions[0]
        else:
            temp_rule_param = {
                "name": source_policy_rule["name"],
                "ruleExpression": source_policy_rule["ruleExpression"],
            }
            ruleParams = source_policy_rule
            actions: list[str] = ruleParams["actions"]
            rule_param_actions = [action.split(".")[1].upper() for action in actions]
            resources: list[str] = ruleParams["resources"]
            resourceType = source_policy_rule["resourceType"]

            ruleParams["vaultID"] = target_vault_id
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
        target_policy_rule_params.append(temp_rule_param)

    update_payload["ruleParams"] = target_policy_rule_params

    return update_payload


def main():
    try:
        source_policy_id = SOURCE_POLICY_ID
        target_policy_id = TARGET_POLICY_ID
        if source_policy_id and target_policy_id:
            source_policy = get_source_policy(source_policy_id)
            target_policy = get_target_policy(target_policy_id)
            policy_payload = transform_policy_payload(source_policy, target_policy)
            update_policy(policy_payload)
            print(f"-- Policy {TARGET_POLICY_ID} updated successfully. --")
        else:
            print("-- Please provide valid input. Missing input paramaters. --")
    except requests.exceptions.HTTPError as http_err:
        print(f"-- update_policy HTTP error: {http_err.response.content.decode()} --")
        raise http_err
    except Exception as err:
        print(f"-- update_policy error: {err} --")
        raise err


if __name__ == "__main__":
    main()
