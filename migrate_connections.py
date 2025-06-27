import ast
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

def get_connection(connection_id):
    # /inboundRoutes can also fetch outbound connection details
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/gateway/inboundRoutes/{connection_id}",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()

def create_connection(connection):
    route = "outboundRoutes" if connection["mode"] == "EGRESS" else "inboundRoutes"
    response = requests.post(
        f"{TARGET_ENV_URL}/v1/gateway/{route}",
        json=connection,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    return response


def transform_connection_payload(source_resource):
    transformed_resource = source_resource
    del transformed_resource["ID"]
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
        if CONNECTIONS_CONFIG is not None and CONNECTIONS_CONFIG != "None":
            print(f"-- Fetching connections from the config file --")
            with open("configs/connections/connections.json", "r") as file:
                content = file.read()
                connections = json.loads(content)
            if CONNECTIONS_CONFIG == "Mastercom" or CONNECTIONS_CONFIG == "Visa Resolve Online":
                if connections[0]["name"] == CONNECTIONS_CONFIG:
                    connections = [connections[0]]
        elif MIGRATE_ALL_CONNECTIONS is not None and MIGRATE_ALL_CONNECTIONS.lower() == "true":
            if SOURCE_VAULT_ID:
                print(f"-- Fetching all connections from the source vault --")
                connections = list_connections(SOURCE_VAULT_ID)
            else:
                print(
                    "-- Please provide valid input. Source vault ID is required to migrate all connections --"
                )
                return
        else:
            connection_ids = (
                connection_ids
                if connection_ids
                else ast.literal_eval(CONNECTION_IDS)
            )
            print(f"-- Fetching connection details for the given connection IDs --")
            for connection_id in connection_ids:
                connection = get_connection(connection_id)
                connections.append(connection)
        created_connections = []
        for index, connection in enumerate(connections):
            print(f"-- Working on connection: {index + 1}. {connection["name"]} --")
            connection_payload = transform_connection_payload(connection)
            create_connection_response = create_connection(connection_payload)
            if create_connection_response.status_code == 200:
                created_connection = create_connection_response.json()
                created_connections.append(created_connection)
                # fetch connection roles
                # create service account and assign connection invoker role
                print(
                f"-- Connection migrated successfully: {connection['name']}. Source CONNECTION_ID: {connection['ID']}, Target CONNECTION_ID: {created_connection['ID']} --"
                )
            else:
                print(f"-- Connection migration failed: {create_connection_response.status_code}. {create_connection_response.content}")
        print(f"-- {len(created_connections)} out of {len(connections)} connections were created successfully. --") 
        print("-- Connections migration script executed successfully. --")
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
