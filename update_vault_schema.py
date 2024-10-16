import requests
import os

SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")
SOURCE_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
TARGET_ACCOUNT_ID = os.getenv("TARGET_ACCOUNT_ID")
SOURCE_ACCOUNT_AUTH = os.getenv("SOURCE_ACCOUNT_AUTH")
TARGET_ACCOUNT_AUTH = os.getenv("TARGET_ACCOUNT_AUTH")
SOURCE_ENV_URL = os.getenv("SOURCE_ENV_URL")
TARGET_ENV_URL = os.getenv("TARGET_ENV_URL")
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")

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

def get_vault_details(vaultID: str):
    response = requests.get(f"{SOURCE_ENV_URL}/v1/vaults/{vaultID}", headers=SOURCE_ACCOUNT_HEADERS)
    response.raise_for_status()
    return response.json()

def update_vault(update_vault_request_payload):
    response = requests.patch(f"{TARGET_ENV_URL}/v1/vaults/{TARGET_VAULT_ID}", json=update_vault_request_payload, headers=TARGET_ACCOUNT_HEADERS)
    response.raise_for_status()
    return response.json()

def transform_payload(vault_details):
    update_vault_payload = {
        "name": vault_details["name"],
        "description": vault_details["description"],
        "vaultSchema" : {
            "schemas": vault_details["schemas"],
            "tags": vault_details["tags"]
        },
    }
    return update_vault_payload
    
def main():
    try:
        if SOURCE_VAULT_ID and TARGET_VAULT_ID:
            print(f"-- Fetching {SOURCE_VAULT_ID} vault details --")
            vault_details = get_vault_details(SOURCE_VAULT_ID)
            print(f"-- Working on updating vault in target account --")
            update_vault_request = transform_payload(vault_details["vault"])
            update_vault_response = update_vault(update_vault_request)
            print(f"-- Vault with ID {update_vault_response['ID']} has been updated successfully in the target account. --")
        else:
            print("-- Please provide valid input. Missing Target Vault ID or Source Vault ID. --")

    except requests.exceptions.HTTPError as http_err:
        print(f"-- update_vault_schema HTTP error: {http_err.response.content.decode()} --")
        exit(1)
    except Exception as err:
        print(f"-- update_vault_schema other error: {err} --")
        exit(1)  

if __name__ == "__main__":
    main()
