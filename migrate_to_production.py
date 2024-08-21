import requests
import os
from migrate_serviceaccounts import main as migrate_service_accounts

# from dotenv import load_dotenv

# load_dotenv()

SOURCE_ENV_URL = "https://manage.skyflowapis-preview.com"

SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")
SOURCE_ENV_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
SOURCE_ENV_AUTH = os.getenv("SOURCE_ENV_AUTH")

SOURCE_ENV_HEADERS = {
    "X-SKYFLOW-ACCOUNT-ID": SOURCE_ENV_ACCOUNT_ID,
    "Authorization": f"Bearer {SOURCE_ENV_AUTH}",
    "Content-Type": "application/json",
}


def list_service_accounts() -> list:
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/serviceAccounts?resource.ID={SOURCE_VAULT_ID}&resource.type=VAULT",
        headers=SOURCE_ENV_HEADERS,
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
        print(f"-- No.of Service accounts: {len(service_account_ids)} --",)
        print("-- Working on Service accounts migration --")
        new_service_accounts = migrate_service_accounts(service_account_ids)
        # print("Service account credentials", [sa for sa in new_service_accounts])
        print("-- !! Governance resources migration to target env done successfully !! --")
    except requests.exceptions.HTTPError as http_err:
        print(f"-- migration HTTP error: {http_err.response.content.decode()} --")
    except Exception as err:
        print(f"-- migration other error: {err} --")


if __name__ == "__main__":
    main()
