import ast
import os
import requests

SOURCE_ROLE_ID = os.getenv("SOURCE_ROLE_ID")
TARGET_ROLE_ID = os.getenv("TARGET_ROLE_ID")
UPDATE_ROLE_CRITERIA = os.getenv("UPDATE_ROLE_CRITERIA")
POLICY_IDS = os.getenv("POLICY_IDS")
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


def get_source_role(policy_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles/{policy_id}", headers=SOURCE_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_target_role(policy_id):
    response = requests.get(
        f"{TARGET_ENV_URL}/v1/roles/{policy_id}", headers=TARGET_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def update_role(role_data):
    response = requests.patch(
        f"{TARGET_ENV_URL}/v1/roles/{TARGET_ROLE_ID}",
        json=role_data,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def transform_role_payload(source_role, target_role):
    role_payload = {"ID":target_role["role"]["ID"], "roleDefinition": {}}
    role_payload["roleDefinition"]["name"] = source_role["role"]["definition"]["name"]
    role_payload["roleDefinition"]["displayName"] = source_role["role"]["definition"]["displayName"]
    role_payload["roleDefinition"]["description"] = source_role["role"]["definition"]["description"]
    return role_payload

def assign_policy_to_role(policy_ids, role_id: list):
    for policy_id in policy_ids:
        assign_request = {"ID": policy_id, "roleIDs": role_id}
        response = requests.post(
            f"{TARGET_ENV_URL}/v1/policies/assign",
            json=assign_request,
            headers=TARGET_ACCOUNT_HEADERS,
        )
        response.raise_for_status()


def main():
    try:
        print("Criteria", UPDATE_ROLE_CRITERIA)
        print("List of Policies", POLICY_IDS)
        source_role_id = SOURCE_ROLE_ID
        target_role_id = TARGET_ROLE_ID
        if source_role_id and target_role_id:
            source_role = get_source_role(source_role_id)
            target_role = get_target_role(target_role_id)
            role_payload = transform_role_payload(source_role, target_role)
            if(UPDATE_ROLE_CRITERIA == "UPDATE_METADATA"):
                update_role(role_payload)
            elif(UPDATE_ROLE_CRITERIA == "ASSIGN_POLICY"):
                if(POLICY_IDS):
                    policy_ids = policy_ids if policy_ids else ast.literal_eval(POLICY_IDS)
                    assign_policy_to_role(policy_ids)
                else:
                    print("Please provide policy IDs to assign.")
            print(f"-- Role {TARGET_ROLE_ID} updated successfully. --")
        else:
            print("-- Please provide valid input. Missing input paramaters. --")
    except requests.exceptions.HTTPError as http_err:
        print(f"-- update_role HTTP error: {http_err.response.content.decode()} --")
        raise http_err
    except Exception as err:
        print(f"-- update_role error: {err} --")
        raise err


if __name__ == "__main__":
    main()
