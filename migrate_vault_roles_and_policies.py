import requests
import os
from migrate_roles import main as migrate_roles

SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")
SOURCE_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
SOURCE_ACCOUNT_AUTH = os.getenv("SOURCE_ACCOUNT_AUTH")
SOURCE_ENV_URL = os.getenv("SOURCE_ENV_URL")

SOURCE_ACCOUNT_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": SOURCE_ACCOUNT_ID,
    "Authorization": f"Bearer {SOURCE_ACCOUNT_AUTH}",
    "Content-Type": "application/json",
}


def list_all_vault_custom_roles() -> list:
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/roles?type=CUSTOM&resource.ID={SOURCE_VAULT_ID}&resource.type=VAULT",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def main():
    try:
        print(f"-- Fetching all ROLES for given VAULT --")
        roles = list_all_vault_custom_roles()
        role_ids = [
            role["ID"]
            for role in roles["roles"]
        ]
        print(
            f"-- No.of Roles: {len(role_ids)} --",
        )
        print("-- Working on Roles migration --")
        migrate_roles(role_ids)
        print(
            f"-- Roles and Policies for given vault {SOURCE_VAULT_ID} are migrated successfully --"
        )
    except requests.exceptions.HTTPError as http_err:
        print(f"-- migrate_vault_roles_and_policies HTTP error: {http_err.response.content.decode()} --")
        exit(1)
    except Exception as err:
        print(f"-- migrate_vault_roles_and_policies other error: {err} --")
        exit(1)


if __name__ == "__main__":
    main()
