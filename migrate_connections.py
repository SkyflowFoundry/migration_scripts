import os
import requests
import json


CONNECTION_IDS = os.getenv("CONNECTION_IDS")
CONNECTIONS_CONFIG = os.getenv("CONNECTIONS_CONFIG")
MIGRATE_ALL_CONNECTIONS = os.getenv("MIGRATE_ALL_CONNECTIONS")
SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")
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


def list_connections(vault_id):
    connections = []
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/gateway/outboundRoutes?vaultID={vault_id}",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    connections.extend(response.json()["ConnectionMappings"])
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/gateway/inboundRoutes?vaultID={vault_id}",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    connections.extend(response.json()["ConnectionMappings"])
    return connections


def create_connection(connection):
    route = "outboundRoutes" if connection["mode"] == "EGRESS" else "inboundRoutes"
    response = requests.post(
        f"{TARGET_ENV_URL}/v1/gateway/{route}",
        json=connection,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def transform_connection_payload(source_resource):
    transformed_resource = source_resource
    transformed_resource["vaultID"] = TARGET_VAULT_ID
    if "BasicAudit" in transformed_resource.keys():
        del transformed_resource["BasicAudit"]
    for route in transformed_resource["routes"]:
        del route["invocationURL"]
    return transformed_resource


def main(connection_ids=None):
    try:
        print("-- Initiating Connections migration --")
        connections = []
        if CONNECTIONS_CONFIG:
            print(f"-- Fetching connections from the config file --")
            with open(CONNECTIONS_CONFIG, "r") as file:
                content = file.read()
                connections = json.loads(content)
        elif MIGRATE_ALL_CONNECTIONS:
            if SOURCE_VAULT_ID:
                connections = list_connections(SOURCE_VAULT_ID)
            else:
                print(
                    "-- Please provide valid input. Source vault ID is required to migrate all connections --"
                )
        else:
            connections = []
            # (ToDo) iterate over connection IDs and fetch connection details
            # connection_ids = (
            #     connection_ids
            #     if connection_ids
            #     else ast.literal_eval(CONNECTION_IDS)
            # )
        created_connections = []
        for index, connection in enumerate(connections):
            print(f"-- Working on connection: {index + 1} {connection["name"]} --")
            connection_payload = transform_connection_payload(connection)
            new_connection = create_connection(connection_payload)
            created_connections.append(new_connection)
            # fetch connection roles
            # create service account and assign connection invoker role
            print(
                f"-- Connection migrated successfully: {connection['name']}. Source CONNECTION_ID: {connection['ID']}, Target CONNECTION_ID: {new_connection['ID']} --"
            )
        print("-- Connections migration script executed successfully --")
    except requests.exceptions.HTTPError as http_err:
        print(
            f"-- migrate_connections HTTP error: {http_err.response.content.decode()} --"
        )
        raise http_err
    except Exception as err:
        print(f"-- migrate_connections other error: {err} --")
        raise err


if __name__ == "__main__":
    main()
