import os
import ast
import requests
from migrate_roles import main as migrate_roles


SERVICE_ACCOUNT_IDS = os.getenv("SERVICE_ACCOUNT_IDS")
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


def list_service_account_roles(service_account_id):
    response = requests.get(
        f"{SOURCE_VAULT_ENV_URL}/v1/members/{service_account_id}/roles?member.type=SERVICE_ACCOUNT",
        headers=SOURCE_VAULT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_service_account(service_account_id):
    response = requests.get(
        f"{SOURCE_VAULT_ENV_URL}/v1/serviceAccounts/{service_account_id}",
        headers=SOURCE_VAULT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def create_service_account(service_account):
    response = requests.post(
        f"{TARGET_VAULT_ENV_URL}/v1/serviceAccounts",
        json=service_account,
        headers=TARGET_VAULT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def assign_roles_to_service_account(role_ids, service_account_id):
    for role_id in role_ids:
        assign_request = {
            "ID": role_id,
            "members": [{"type": "SERVICE_ACCOUNT", "ID": service_account_id}],
        }
        response = requests.post(
            f"{TARGET_VAULT_ENV_URL}/v1/roles/assign",
            json=assign_request,
            headers=TARGET_VAULT_HEADERS,
        )
        response.raise_for_status()


def transform_service_account_payload(source_resource):
    tramsformed_resource = source_resource
    tramsformed_resource["resource"] = {"ID": TARGET_VAULT_ID, "type": "VAULT"}
    del tramsformed_resource["serviceAccount"]["ID"]
    del tramsformed_resource["serviceAccount"]["namespace"]
    del tramsformed_resource["serviceAccount"]["BasicAudit"]
    return tramsformed_resource


def main(service_accounts_ids=None):
    try:
        service_accounts_ids = (
            service_accounts_ids
            if service_accounts_ids
            else ast.literal_eval(SERVICE_ACCOUNT_IDS)
        )
        created_service_accounts = []
        for index, service_account_id in enumerate(service_accounts_ids):
            print(f"-- Working on SA: {index + 1} --")
            service_account_resource = get_service_account(service_account_id)
            service_account_payload = transform_service_account_payload(
                service_account_resource
            )
            new_service_account = create_service_account(service_account_payload)
            created_service_accounts.append(new_service_account)
            print(f"-- Fetching ROLES --")
            service_account_roles = list_service_account_roles(service_account_id)
            service_account_roles_ids = [
                service_account_role["role"]["ID"]
                for service_account_role in service_account_roles["roleToResource"]
            ]
            print(f"-- No.of roles for SA: {len(service_account_roles_ids)} --")
            roles_created = migrate_roles(service_account_roles_ids)
            created_role_ids = [role["ID"] for role in roles_created]
            assign_roles_to_service_account(
                created_role_ids, new_service_account["clientID"]
            )
        print("-- SERVICE_ACCOUNTS Migration done --")
        return created_service_accounts
    except requests.exceptions.HTTPError as http_err:
        print(
            f"-- migrate_service_accounts HTTP error: {http_err.response.content.decode()} --"
        )
        raise http_err
    except Exception as err:
        print(f"-- migrate_service_accounts other error: {err} --")
        raise err


if __name__ == "__main__":
    main()
