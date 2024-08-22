# Skyflow Migration Scripts

This repository contains migration scripts to manage and migrate various components of your Skyflow vault. The scripts are designed to be executed using GitHub workflows, enabling automated and streamlined migration processes.

## Migration Scripts

### 1. Policies Migration

Migrates specific policies from the source Vault to the target Vault.

#### Parameters:
- **`target_vault_id`**: Target Vault ID.
- **`policy_ids`**: A list of policy IDs to be migrated.
- **`source_vault_access_token`**: Access token for the source Vault.
- **`target_vault_access_token`**: Access token for the target Vault.

### 2. Roles Migration

Migrates specific roles from the source Skyflow Vault to the target Vault.

#### Parameters:
- **`target_vault_id`**: Target Vault ID.
- **`role_ids`**: A list of role IDs to be migrated.
- **`source_vault_access_token`**: Access token for the source Vault.
- **`target_vault_access_token`**: Access token for the target Vault.

### 3. Service Accounts Migration

Migrates specific service accounts from the source Skyflow Vault to the target Vault.

#### Parameters:
- **`target_vault_id`**: Target Vault ID.
- **`service_account_ids`**: A list of service account IDs to be migrated.
- **`source_vault_access_token`**: Access token for the source Vault.
- **`target_vault_access_token`**: Access token for the target Vault.

### 4. Complete Governance Migration

Migrates the complete governance setup, including policies, roles, and service accounts, from the source Skyflow vault to the target vault.

#### Parameters:
- **`source_vault_id`**: Source Vault ID.
- **`target_vault_id`**: Target Vault ID.
- **`source_vault_access_token`**: Access token for the source Vault.
- **`target_vault_access_token`**: Access token for the target Vault.


## Running the Scripts

These scripts can be executed through GitHub workflows. Each script requires the appropriate parameters and Vault variables to be set for successful migration.

### Step 1: Set Up GitHub Repository Variables

## Repository Variables

Ensure the following repository variables are set before running the workflows:

- `SOURCE_VAULT_ENV_URL`: Management URL of the source Vault.
- `TARGET_VAULT_ENV_URL`: Management URL of the target Vault.
- `SOURCE_VAULT_ACCOUNT_ID`: Account ID for the source Vault.
- `TARGET_VAULT_ACCOUNT_ID`: Account ID for the target Vault.

### Step 2: Run the Workflow

To run the migration scripts, ensure that you provide the necessary input parameters and repository variables. Simply trigger the workflow with the correct inputs, and let the workflow do the magic to seamlessly migrate your Skyflow resources!