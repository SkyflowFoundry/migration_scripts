import os
import ast
import requests
from migrate_roles import main as migrate_roles


SERVICE_ACCOUNT_IDS = os.getenv("SERVICE_ACCOUNT_IDS")
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")
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


def list_service_account_roles(service_account_id):
    """Return every role assigned to the given service account."""
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/members/{service_account_id}/roles?member.type=SERVICE_ACCOUNT",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_service_account(service_account_id):
    """Fetch a service account definition from the source account."""
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/serviceAccounts/{service_account_id}",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def create_service_account(service_account):
    """Create the supplied service account in the target account."""
    response = requests.post(
        f"{TARGET_ENV_URL}/v1/serviceAccounts",
        json=service_account,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def assign_roles_to_service_account(role_ids, service_account_id):
    """Attach the specified roles to the new service account."""
    for role_id in role_ids:
        assign_request = {
            "ID": role_id,
            "members": [{"type": "SERVICE_ACCOUNT", "ID": service_account_id}],
        }
        response = requests.post(
            f"{TARGET_ENV_URL}/v1/roles/assign",
            json=assign_request,
            headers=TARGET_ACCOUNT_HEADERS,
        )
        response.raise_for_status()


def transform_service_account_payload(source_resource):
    """Strip source-only metadata before creating the service account."""
    transformed_resource = source_resource
    # transformed_resource["resource"] = {"ID": TARGET_VAULT_ID, "type": "VAULT"} // not require due to SA flattening change
    del transformed_resource["serviceAccount"]["ID"]  # IDs are regenerated per account
    del transformed_resource["serviceAccount"]["namespace"]
    del transformed_resource["serviceAccount"]["BasicAudit"]
    return transformed_resource


def main(service_accounts_ids=None):
    """Migrates service accounts and associated roles."""
    try:
        print("-- Initializing Service accounts migration --")
        service_accounts_ids = (
            service_accounts_ids
            if service_accounts_ids
            else ast.literal_eval(SERVICE_ACCOUNT_IDS)
        )
        created_service_accounts = []
        for index, service_account_id in enumerate(service_accounts_ids):
            service_account_resource = get_service_account(service_account_id)
            print(f"-- Working on Service account: {index + 1}  {service_account_resource['serviceAccount']['name']} --")
            service_account_payload = transform_service_account_payload(
                service_account_resource
            )
            print("-- Creating Service account --")
            new_service_account = create_service_account(service_account_payload)
            created_service_accounts.append(new_service_account)
            print(f"-- Fetching Roles --")
            service_account_roles = list_service_account_roles(service_account_id)
            service_account_roles_ids = [
                service_account_role["role"]["ID"]
                for service_account_role in service_account_roles["roleToResource"]
            ]
            no_of_roles = len(service_account_roles_ids)
            if(no_of_roles == 0):
                print(f"-- No Roles found for {service_account_resource['serviceAccount']['name']} --")
            else:
                print(f"-- Working on Roles migration. No.of Roles for {service_account_resource['serviceAccount']['name']}: {no_of_roles} --")
                roles_created = migrate_roles(service_account_roles_ids)
                created_role_ids = [role["ID"] for role in roles_created]
                assign_roles_to_service_account(
                created_role_ids, new_service_account["clientID"]
                )
            print(f"-- Service account migrated succesfully: {service_account_resource['serviceAccount']['name']}. Source SERVICE_ACCOUNT_ID: {service_account_id}, Target SERVICE_ACCOUNT_ID: {new_service_account['clientID']} --")
        print("-- Service account migration script executed successfully --")        
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
