# Skyflow Migration Scripts

This repository contains migration scripts to manage and migrate various resources from one account to other. The scripts are designed to be executed using GitHub workflows, enabling automated and streamlined migration processes.

## Governance Migration

### 1. Policies Migration

Migrates specific policies from the source Vault to the target Vault.

#### Parameters:
- **`target_vault_id`**: Target Vault ID.
- **`policy_ids`**: A list of policy IDs to be migrated. Get Policy Ids from Studio.
- **`source_account_access_token`**: Access token of the source account.
- **`target_account_access_token`**: Access token of the target account.

### 2. Roles Migration

Migrates specific roles from the source Skyflow Vault to the target Vault. This will also migrate underlying policies for a given role. 

Note: Using existing policies for a new role will result in duplicate name conflict error. Make sure that the role and underlying policies are new ones.

#### Parameters:
- **`target_vault_id`**: Target Vault ID.
- **`role_ids`**: A list of role IDs to be migrated. Get Role Ids from Studio.
- **`source_account_access_token`**: Access token of the source account.
- **`target_account_access_token`**: Access token of the target account.

### 3. Service Accounts Migration

Migrates specific service accounts from the source Skyflow Vault to the target Vault. This will also migrate underlying roles and policies for a given Servce account. 

Note: Using existing roles / policies for a new service account will result in duplicate name conflict error. Make sure that the service account, underlying roles and policies are new ones.

#### Parameters:
- **`target_vault_id`**: Target Vault ID.
- **`service_account_ids`**: A list of service account IDs to be migrated. Get Service account Ids from Studio.
- **`source_account_access_token`**: Access token of the source account.
- **`target_account_access_token`**: Access token of the target account.

### 4. Complete Governance Migration

Migrates the complete governance setup, including policies, roles, and service accounts, from the source Skyflow vault to the target vault.

#### Parameters:
- **`source_vault_id`**: Source Vault ID.
- **`target_vault_id`**: Target Vault ID.
- **`source_account_access_token`**: Access token of the source account.
- **`target_account_access_token`**: Access token of the target account.

## Vault Schema Migration

Use this script to create a vault with the source vault schema in the target account.

#### Parameters:
- **`source_vault_id`**: Source Vault ID.
- **`workspace_id`**: Workspace ID of the target account.
- **`vault_name`**: (Optional) Name for the target vault. If not given, source vault name will be used.
- **`vault_description`**: (Optional) Description for the target vault. If not given, source vault description will be used.
- **`source_account_access_token`**: Access token of the source account.
- **`target_account_access_token`**: Access token of the target account. Use the access token generated from Studio.

## Vault Schema + Governance Migration

Use this script to create a vault with the source vault schema and in to migrate Governance resource for the given vault inthe target account.

#### Parameters:
- **`source_vault_id`**: Source Vault ID.
- **`workspace_id`**: Workspace ID of the target account.
- **`vault_name`**: (Optional) Name for the target vault. If not given, source vault name will be used.
- **`vault_description`**: (Optional) Description for the target vault. If not given, source vault description will be used.
- **`source_account_access_token`**: Access token of the source account.
- **`target_account_access_token`**: Access token of the target account. Use the access token generated from Studio.

## Running the Scripts

These scripts can be executed through GitHub workflows. Each script requires the appropriate parameters and Vault variables to be set for successful migration.

### Step 1: Set Up GitHub Repository Variables

## Repository Variables

Ensure the following repository variables are set before running the workflows:

- `SOURCE_ENV_URL`: Management URL of the source Vault.
- `TARGET_ENV_URL`: Management URL of the target Vault.
- `SOURCE_ACCOUNT_ID`: Account ID for the source Vault.
- `TARGET_ACCOUNT_ID`: Account ID for the target Vault.

### Step 2: Run the Workflow

To run the migration scripts, ensure that you provide the necessary input parameters and repository variables. Simply trigger the workflow with the correct inputs, and let the workflow do the magic to seamlessly migrate your Skyflow resources!

### Step 3: Get your Credentials file (Applicable for SA/Vault Governance migration)

- Re-Key the SA to get credentials from [Studio or API](https://docs.skyflow.com/rotate-service-account-keys/#prerequisites)
- Secure service account credentials by storing them in designated secret stores with built-in security, and securely pass info to runtime applications.