import ast
import requests
import os
from migrate_policies import main as migrate_policies


SYSTEM_ROLES = ["VAULT_OWNER", "VAULT_EDITOR", "VAULT_VIEWER", "PIPELINE_MANAGER", "CONNECTION_MANAGER"]

ROLE_IDS = os.getenv("ROLE_IDS") 
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")
SOURCE_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
TARGET_ACCOUNT_ID = os.getenv("TARGET_ACCOUNT_ID")
SOURCE_ACCOUNT_AUTH = os.getenv("SOURCE_ACCOUNT_AUTH")
TARGET_ACCOUNT_AUTH = os.getenv("TARGET_ACCOUNT_AUTH")
SOURCE_ENV_URL = os.getenv("SOURCE_ENV_URL")
TARGET_ENV_URL = os.getenv("TARGET_ENV_URL")
MIGRATE_ALL_ROLES = os.getenv("MIGRATE_ALL_ROLES")
SKIP_ROLE_CREATION_IF_ROLE_EXISTS = os.getenv("SKIP_ROLE_CREATION_IF_ROLE_EXISTS")
SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")

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


def get_role(role_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles/{role_id}", headers=SOURCE_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()

def get_system_role(role_name):
    response = requests.get(
        f"{TARGET_ENV_URL}/v1/roles?name={role_name}&resource.type=VAULT&resource.ID={TARGET_VAULT_ID}", headers=TARGET_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()    

def create_role(role):
    response = requests.post(
        f"{TARGET_ENV_URL}/v1/roles", json=role, headers=TARGET_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_role_policies(role_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles/{role_id}/policies", headers=SOURCE_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_role_by_role_name(role_name):
    response = requests.get(
        f"{TARGET_ENV_URL}/v1/roles?name={role_name}&resource.type=VAULT&resource.ID={TARGET_VAULT_ID}",
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def assign_policy_to_role(policy_ids, role_id: list):
    for policy_id in policy_ids:
        assign_request = {"ID": policy_id, "roleIDs": role_id}
        response = requests.post(
            f"{TARGET_ENV_URL}/v1/policies/assign",
            json=assign_request,
            headers=TARGET_ACCOUNT_HEADERS,
        )
        response.raise_for_status()
    # return response.json()

def list_all_roles() -> list:
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles?type=CUSTOM&resource.ID={SOURCE_VAULT_ID}&resource.type=VAULT",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


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

def main(role_ids=None):
    try:
        should_enable_custom_role_check = SKIP_ROLE_CREATION_IF_ROLE_EXISTS
        if MIGRATE_ALL_ROLES:
            if(SOURCE_VAULT_ID):
                role_ids = list_all_roles()
            else:
                print("-- Please provide valid input. Source vault ID is required to migrate all roles --")
        else:
            role_ids = ast.literal_eval(ROLE_IDS)
        roles_created = []
        for index, role_id in enumerate(role_ids):
            print(f"-- Working on Role: {index + 1}  --")
            role_info = get_role(role_id)
            role_name = role_info["role"]["definition"]["name"]
            if(role_name in SYSTEM_ROLES):
                print('-- SYSTEM_ROLE found, fetching SYSTEM_ROLE ID from target Vault --')
                system_role = get_system_role(role_name)
                roles_created.append({"ID": system_role["roles"][0]["ID"]})
            else:
                should_create_role = True
                if(should_enable_custom_role_check):
                    print('-- checking if a role exists for the given vault --')
                    role_response = get_role_by_role_name(role_name)
                    if(len(role_response["roles"]) == 1):
                        print("-- Found an existing CUSTOM_ROLE, skipping role creation --")
                        should_create_role = False
                        roles_created.append({"ID" : role_response["roles"][0]["ID"]})
                    else:
                        print("-- Role does not exist --") 
                if(should_create_role):
                    role_payload = transform_role_payload(role_info)
                    print(f"-- Creating role --")
                    new_role = create_role(role_payload)
                    roles_created.append(new_role)
                    print(f"-- Fetching policies for the given Role --")
                    role_policies = get_role_policies(role_id)
                    policy_ids = [policy["ID"] for policy in role_policies["policies"]]
                    no_of_policies = len(policy_ids)
                    if(no_of_policies == 0):
                        print('-- No policies found for the given role --')
                    else:
                        print(f"-- Working on policies migration. No. of policies found for given role: {no_of_policies} --")
                        policies_created = migrate_policies(policy_ids)
                        created_policy_ids = [policy["ID"] for policy in policies_created]
                        assign_policy_to_role(created_policy_ids, [new_role["ID"]])
                    print(f"-- Role migration completed: {role_name}. Source ROLE_ID: {role_id}, Target ROLE_ID: {new_role['ID']} --")        
        return roles_created
    except requests.exceptions.HTTPError as http_err:
        print(f'-- Role creation failed for {role_id}. Role with name {role_name} already exists in target account. Please update this role name in your source account and try again. --')
        print(f'-- migrate_roles HTTP error: {http_err.response.content.decode()} --')
        raise http_err
    except Exception as err:
        print(f'-- migrate_roles error: {err} --')
        raise err

if __name__ == "__main__":
    main()
