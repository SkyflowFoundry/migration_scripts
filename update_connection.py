import copy
import os
import requests

SOURCE_CONNECTION_ID = os.getenv("SOURCE_CONNECTION_ID")
TARGET_CONNECTION_ID = os.getenv("TARGET_CONNECTION_ID")
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

def get_connection(connection_id: str, env_url: str, headers: dict) -> dict:
    response = requests.get(
        f"{env_url}/v1/gateway/inboundRoutes/{connection_id}", headers=headers
    )
    response.raise_for_status()
    return response.json()

def update_connection(connection_id: str, connection_payload: dict):
    mode = 'inboundRoutes' if connection_payload["mode"] == "INGRESS" else 'outboundRoutes'
    response = requests.put(
        f"{TARGET_ENV_URL}/v1/gateway/{mode}/{connection_id}",
        json=connection_payload,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()

def transform_connection_payload(source_connection: dict, target_connection: dict):
    transformed_connection = copy.deepcopy(source_connection)
    transformed_connection["ID"] = target_connection["ID"]
    transformed_connection["vaultID"] = target_connection["vaultID"]
    transformed_connection.pop("BasicAudit", None)

    for route in transformed_connection.get("routes", []):
        route.pop("invocationURL", None)

    return transformed_connection

def main():
    try:
        if not SOURCE_CONNECTION_ID or not TARGET_CONNECTION_ID:
            print("-- Please provide valid input. Missing connection IDs --")
            return

        print(f"-- Fetching source connection details:{SOURCE_CONNECTION_ID} --")
        source_connection = get_connection(
            SOURCE_CONNECTION_ID, SOURCE_ENV_URL, SOURCE_ACCOUNT_HEADERS
        )
        print(f"-- Fetching target connection details:{TARGET_CONNECTION_ID} --")
        target_connection = get_connection(
            TARGET_CONNECTION_ID, TARGET_ENV_URL, TARGET_ACCOUNT_HEADERS
        )
        print("-- Working on updating connection in target account --")
        connection_payload = transform_connection_payload(
            source_connection, target_connection
        )
        update_response = update_connection(TARGET_CONNECTION_ID, connection_payload)
        print(
            f"-- Connection updated successfully. Source CONNECTION_ID: {SOURCE_CONNECTION_ID}. Target CONNECTION_ID: {update_response['ID']} --"
        )
    except requests.exceptions.HTTPError as http_err:
        print(f"-- update_connection HTTP error: {http_err.response.content.decode()} --")
        exit(1)
    except Exception as err:
        print(f"-- update_connection error: {err} --")
        exit(1)

if __name__ == "__main__":
    main()
