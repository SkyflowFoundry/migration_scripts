import ast
import requests
import os
from migrate_policies import main as migrate_policies

# from dotenv import load_dotenv

# load_dotenv()

SOURCE_ENV_URL = "https://manage.skyflowapis-preview.com"
TARGET_ENV_URL = "https://manage.skyflowapis.com"

SYSTEM_ROLES = ["VAULT_OWNER", "VAULT_EDITOR", "VAULT_VIEWER", "PIPELINE_MANAGER", "CONNECTION_MANAGER"]

ROLE_IDS = os.getenv("ROLE_IDS") 
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")
SOURCE_ENV_ACCOUNT_ID = os.getenv("SOURCE_ENV_ACCOUNT_ID")
TARGET_ENV_ACCOUNT_ID = os.getenv("TARGET_ENV_ACCOUNT_ID")
SOURCE_ENV_AUTH = os.getenv("SOURCE_ENV_AUTH")
TARGET_ENV_AUTH = os.getenv("TARGET_ENV_AUTH")

SOURCE_ENV_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": SOURCE_ENV_ACCOUNT_ID,
    "Authorization": f"Bearer {SOURCE_ENV_AUTH}",
    "Content-Type": "application/json",
}

TARGET_ENV_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": TARGET_ENV_ACCOUNT_ID,
    "Authorization": f"Bearer {TARGET_ENV_AUTH}",
    "Content-Type": "application/json",
}


def get_role(role_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles/{role_id}", headers=SOURCE_ENV_HEADERS
    )
    response.raise_for_status()
    return response.json()

def get_system_role(role_name):
    response = requests.get(
        f"{TARGET_ENV_URL}/v1/roles?name={role_name}&resource.type=VAULT&resource.ID={TARGET_VAULT_ID}", headers=TARGET_ENV_HEADERS
    )
    response.raise_for_status()
    return response.json()    

def create_role(role):
    response = requests.post(
        f"{TARGET_ENV_URL}/v1/roles", json=role, headers=TARGET_ENV_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_role_policies(role_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles/{role_id}/policies", headers=SOURCE_ENV_HEADERS
    )
    response.raise_for_status()
    return response.json()


def assign_policy_to_role(policy_ids, role_id: list):
    for policy_id in policy_ids:
        assign_request = {"ID": policy_id, "roleIDs": role_id}
        response = requests.post(
            f"{TARGET_ENV_URL}/v1/policies/assign",
            json=assign_request,
            headers=TARGET_ENV_HEADERS,
        )
        response.raise_for_status()
    # return response.json()


def transform_role_payload(source_resource):
    transformed_resource = {}
    transformed_resource["roleDefinition"] = source_resource["role"]["definition"]
    permissions: list = source_resource["role"]["definition"]["permissions"]
    new_permissions = [
        permission
        for permission in permissions
        if permission
        not in [
            "accounts.read:upstream",
            "workspaces.read:upstream",
            "vaults.read:upstream",
        ]
    ]
    transformed_resource["roleDefinition"]["permissions"] = new_permissions
    transformed_resource["resource"] = {"ID": TARGET_VAULT_ID, "type": "VAULT"}
    return transformed_resource


def main(role_ids=ROLE_IDS):
    try:
        role_ids = role_ids if role_ids else ast.literal_eval(ROLE_IDS)
        roles_created = []
        for index, role_id in enumerate(role_ids):
            print(f"-- Working on {index + 1} ROLE --")
            role_info = get_role(role_id)
            if(role_info["role"]["definition"]["name"] in SYSTEM_ROLES):
                print('-- SYSTEM_ROLE found, fetching SYSTEM_ROLE ID from target env --')
                system_role = get_system_role(role_info["role"]["definition"]["name"])
                roles_created.append({"ID": system_role["roles"][0]["ID"]})
            else:
                role_payload = transform_role_payload(role_info)
                new_role = create_role(role_payload)
                roles_created.append(new_role)
                print(f"-- Fetching POLICIES for given ROLE --")
                role_policies = get_role_policies(role_id)
                policy_ids = [policy["ID"] for policy in role_policies["policies"]]
                print(f"-- Working on POLICIES migration --")
                policies_created = migrate_policies(policy_ids)
                created_policy_ids = [policy["ID"] for policy in policies_created]
                assign_policy_to_role(created_policy_ids, [new_role["ID"]])
        print(f"-- ROLES Migration done --")        
        return roles_created
    except requests.exceptions.HTTPError as http_err:
        print(f'-- migrate_roles HTTP error: {http_err.response.content.decode()} --')
    except Exception as err:
        print(f'-- migrate_roles error: {err} --')

if __name__ == "__main__":
    main()
