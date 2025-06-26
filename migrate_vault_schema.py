import requests
import os
import json
import random

SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")
SOURCE_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
TARGET_ACCOUNT_ID = os.getenv("TARGET_ACCOUNT_ID")
SOURCE_ACCOUNT_AUTH = os.getenv("SOURCE_ACCOUNT_AUTH")
TARGET_ACCOUNT_AUTH = os.getenv("TARGET_ACCOUNT_AUTH")
SOURCE_ENV_URL = os.getenv("SOURCE_ENV_URL")
TARGET_ENV_URL = os.getenv("TARGET_ENV_URL")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")
VAULT_NAME = os.getenv("VAULT_NAME")
VAULT_DESCRIPTION = os.getenv("VAULT_DESCRIPTION")
VAULT_SCHEMA_CONFIG = os.getenv("VAULT_SCHEMA_CONFIG")

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

def create_vault(create_vault_request_payload):
    response = requests.post(f"{TARGET_ENV_URL}/v1/vaults", json=create_vault_request_payload, headers=TARGET_ACCOUNT_HEADERS)
    response.raise_for_status()
    return response.json()

def transform_payload(vault_details):
    create_vault_payload = {
        "name": VAULT_NAME if VAULT_NAME else f"UntitledVault{random.randint(0,1000)}" if VAULT_SCHEMA_CONFIG else vault_details["name"],
        "description": VAULT_DESCRIPTION if VAULT_DESCRIPTION else "" if VAULT_SCHEMA_CONFIG else vault_details["description"],
        "vaultSchema" : {
            "schemas": vault_details["schemas"],
            "tags": vault_details["tags"]
        },
        "workspaceID": WORKSPACE_ID
    }
    return create_vault_payload
    
def main():
    try:
        print("-- Initializing Vault migration --")
        if VAULT_SCHEMA_CONFIG is not None and VAULT_SCHEMA_CONFIG == "config_file":
            print(f"-- Fetching the schema from the config file --")
            with open("configs/connections/schema.json", "r") as file:
                content = file.read()
                schema = json.loads(content)
                vault_details = {
                    "schemas": schema["schemas"],
                    "tags": schema["tags"]
                }
        elif SOURCE_VAULT_ID:
            print(f"-- Fetching {SOURCE_VAULT_ID} vault details --")
            vault_details = get_vault_details(SOURCE_VAULT_ID)["vault"]
        else:
            print("-- Please provide source vault ID or select schema config file --")
        if WORKSPACE_ID:
            print(f"-- Working on creating vault in target account --")
            create_vault_request = transform_payload(vault_details)
            create_vault_response = create_vault(create_vault_request)
            print(f"-- Vault with ID {create_vault_response['ID']} has been created successfully in the target account --")
            if os.getenv("MIGRATE_GOVERNANCE"):
                env_file = os.getenv('GITHUB_ENV')
                with open(env_file, "a") as file:
                    file.write(f"TARGET_VAULT_ID={create_vault_response['ID']}")
        else:
            print("-- Please provide valid input. Workspace ID is missing. --")

    except requests.exceptions.HTTPError as http_err:
        print(f"-- migrate_vault_schema HTTP error: {http_err.response.content.decode()} --")
        exit(1)
    except Exception as err:
        print(f"-- migrate_vault_schema other error: {err} --")
        exit(1)  

if __name__ == "__main__":
    main()
