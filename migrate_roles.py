import requests
import os

# Environment variables for credentials and IDs
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")
ROLE_ID = os.getenv("ROLE_ID")

# Headers with authorization
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

def create_role(role_data):
    response = requests.post(f"{API_BASE_URL}/roles", json=role_data, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()

def get_role_policies(role_id):
    response = requests.get(f"{API_BASE_URL}/roles/{role_id}/policies", headers=headers)
    response.raise_for_status()
    return response.json()

def create_policy(policy_data):
    response = requests.post(f"{API_BASE_URL}/policies", json=policy_data, headers=headers)
    response.raise_for_status()
    return response.json()

def assign_policy_to_role(role_id, policy_id):
    data = {"policy_id": policy_id}
    response = requests.post(f"{API_BASE_URL}/roles/{role_id}/policies", json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    # Example role and policy data
    roles_data = [{"name": "role1"}, {"name": "role2"}]
    policies_data = [{"name": "policy1"}, {"name": "policy2"}]

    # Create roles
    for role_data in roles_data:
        role = create_role(role_data)
        print(f"Created role: {role['id']}")

    # Get policies for the role
    role_policies = get_role_policies(ROLE_ID)
    print(f"Policies for role {ROLE_ID}: {role_policies}")

    # Create policies and assign them to the role
    for policy_data in policies_data:
        policy = create_policy(policy_data)
        print(f"Created policy: {policy['id']}")

        # Assign policy to role
        assign_response = assign_policy_to_role(ROLE_ID, policy['id'])
        print(f"Assigned policy {policy['id']} to role {ROLE_ID}: {assign_response}")

if __name__ == "__main__":
    main()
