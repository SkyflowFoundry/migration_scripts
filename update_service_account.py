import os
import requests

SOURCE_SERVICE_ACCOUNT_ID = os.getenv("SOURCE_SERVICE_ACCOUNT_ID")
TARGET_SERVICE_ACCOUNT_ID = os.getenv("TARGET_SERVICE_ACCOUNT_ID")
UPDATE_SERVICE_ACCOUNT_CRITERIA = os.getenv("UPDATE_SERVICE_ACCOUNT_CRITERIA")
ROLE_IDS = os.getenv("ROLE_IDS")
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


def get_source_service_account(policy_id):
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/policies/{policy_id}", headers=SOURCE_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_target_service_account(policy_id):
    response = requests.get(
        f"{TARGET_ENV_URL}/v1/policies/{policy_id}", headers=TARGET_ACCOUNT_HEADERS
    )
    response.raise_for_status()
    return response.json()


def update_service_account(role_data):
    response = requests.patch(
        f"{TARGET_ENV_URL}/v1/roles/{TARGET_SERVICE_ACCOUNT_ID}",
        json=role_data,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()


def transform_service_account_payload(source_policy, target_policy):
    # TODO
    return

def assign_roles_to_service_account(role_ids, service_account_id):
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

def main():
    try:
        print("Criteria", UPDATE_SERVICE_ACCOUNT_CRITERIA)
        print("List of Roles", ROLE_IDS)
        source_service_account_id = SOURCE_SERVICE_ACCOUNT_ID
        target_service_account_id = TARGET_SERVICE_ACCOUNT_ID
        if source_service_account_id and target_service_account_id:
            source_service_account = get_source_service_account(source_service_account_id)
            target_service_account = get_target_service_account(target_service_account_id)
            service_account_payload = transform_service_account_payload(source_service_account, target_service_account)
            # should assign roles according to criteria
            update_service_account(service_account_payload)
            print(f"-- Service account {TARGET_SERVICE_ACCOUNT_ID} updated successfully. --")
        else:
            print("-- Please provide valid input. Missing input paramaters. --")
    except requests.exceptions.HTTPError as http_err:
        print(f"-- update_service_account HTTP error: {http_err.response.content.decode()} --")
        raise http_err
    except Exception as err:
        print(f"-- update_service_account error: {err} --")
        raise err


if __name__ == "__main__":
    main()
