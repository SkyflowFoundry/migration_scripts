# Skyflow Initial Connection Setup

## Overview

This repository provides scripts for creating initial connections and routes for the Card Network APIs. These connections and routes allow secure integration between the Skyflow vault and card provider services or applications, enabling secure data exchange while maintaining privacy controls.

The scripts are designed to be executed using GitHub workflows, enabling automated and streamlined creation of Skyflow connections and routes. These workflows are set up to run using GitHub Actions, enabling you to create connections with ease. Simply fork the repository and configure the workflows.

## Prerequisites

- Create a GitHub account and log in
- Fork the repository into your account (Please refer to [this documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) to fork the repo)

## Creating Skyflow Connections for Visa and Mastercom

This section describes how to create connections and routes from a config file to the target vault. Source input can be one of the following:

> **Note**: If all values are provided, `config_file` will take priority and the rest of the parameters will be ignored. Likewise, if `migrate_all_connections` is checked, the `connection_ids` parameter will be ignored.

### Input Parameters

| Parameter | Description |
|-----------|-------------|
| `source_and_target_env` | Source and Target environments |
| `config_file` | Connections configurations file. The config file should be present at `configs/connections/connections.json` |
| `target_vault_id` | Target Vault ID |
| `target_account_access_token` | Access token of the target account |

### Optional Parameters

| Parameter | Description |
|-----------|-------------|
| `migrate_all_connections` | If checked, migrates all the connections of the given source vault to the target vault |
| `source_vault_id` | Source Vault ID. This is a required parameter if `migrate_all_connections` is checked |
| `connection_ids` | A list of connection IDs to be migrated. Get Connection IDs from Studio. Ex: `['connection1','connection2']` |
| `source_account_access_token` | Access token of the source account |

## Running the Workflows

Follow these steps to run the workflows and create connections and routes in your Vault:

### Step 1: Set Up GitHub Repository Variables

Ensure the following repository variables are set before running the workflows:

| Variable | Description |
|----------|-------------|
| `SOURCE_ACCOUNT_ID` | Account ID for the source vault |
| `TARGET_ACCOUNT_ID` | Account ID for the target vault |

> **Note**: You can also provide these values during workflow execution.

### Step 2: Run the Workflow

Follow [GitHub's documentation](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/manually-running-a-workflow) on manually running workflows.

To run the connection creation scripts:
1. Navigate to the Actions tab in your forked repository.
2. Select the appropriate workflow.
3. Provide the necessary input parameters and repository variables.
4. Trigger the workflow with the correct inputs.

The workflow will automatically create your Skyflow connections!

## Running Actions on Protected Branch

Reach out to Skyflow Support (support@skyflow.com) to create your protected branch.
