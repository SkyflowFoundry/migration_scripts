import requests
import os
from migrate_service_accounts import main as migrate_service_accounts


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


def list_service_accounts() -> list:
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/serviceAccounts?resource.ID={SOURCE_VAULT_ID}&resource.type=VAULT",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def main():
    try:
        print(f"-- Fetching Service accounts for given VAULT --")
        service_accounts = list_service_accounts()
        service_account_ids = [
            service_account["serviceAccount"]["ID"]
            for service_account in service_accounts["serviceAccounts"]
        ]
        print(
            f"-- No.of Service accounts: {len(service_account_ids)} --",
        )
        print("-- Working on Service accounts migration --")
        new_service_accounts = migrate_service_accounts(service_account_ids)
        print(
            f"-- Governance resources are migrated and applied on {TARGET_VAULT_ID} successfully. --"
        )
    except requests.exceptions.HTTPError as http_err:
        print(f"-- migrate_governance HTTP error: {http_err.response.content.decode()} --")
        exit(1)
    except Exception as err:
        print(f"-- migrate_governance other error: {err} --")
        exit(1)


if __name__ == "__main__":
    main()
