import copy
import json
import os
import requests
from typing import Any, Dict, List, Optional


PIPELINE_ID = os.getenv("PIPELINE_ID")
SOURCE_VAULT_ID = os.getenv("SOURCE_VAULT_ID")
TARGET_VAULT_ID = os.getenv("TARGET_VAULT_ID")
SOURCE_ACCOUNT_ID = os.getenv("SOURCE_ACCOUNT_ID")
TARGET_ACCOUNT_ID = os.getenv("TARGET_ACCOUNT_ID")
SOURCE_ACCOUNT_AUTH = os.getenv("SOURCE_ACCOUNT_AUTH")
TARGET_ACCOUNT_AUTH = os.getenv("TARGET_ACCOUNT_AUTH")
SOURCE_ENV_URL = os.getenv("SOURCE_ENV_URL")
TARGET_ENV_URL = os.getenv("TARGET_ENV_URL")
SOURCE_DATASTORE_CONFIG = os.getenv("SOURCE_DATASTORE_CONFIG")
TARGET_DATASTORE_CONFIG = os.getenv("TARGET_DATASTORE_CONFIG")

FTP_ALLOWED_KEYS = {"transferProtocol", "plainText", "encrypted", "skyflowHosted"}
S3_ALLOWED_KEYS = {"name", "region", "assumedRoleARN"}

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

def list_pipelines(vault_id: str) -> List[Dict[str, Any]]:
    """Return all pipelines in the supplied vault."""
    pipelines = []
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/pipelines?vaultID={vault_id}",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    pipelines.extend(response.json()["pipelines"])
    return pipelines

def get_pipeline(pipeline_id: str) -> Dict[str, Any]:
    """Fetch a single pipeline definition from the source environment."""
    response = requests.get(
        f"{SOURCE_ENV_URL}/v1/pipelines/{pipeline_id}",
        headers=SOURCE_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response.json()["pipeline"]

def create_pipeline(pipeline: Dict[str, Any]) -> requests.Response:
    """Create a pipeline in the target environment."""
    response = requests.post(
        f"{TARGET_ENV_URL}/v1/pipelines",
        json=pipeline,
        headers=TARGET_ACCOUNT_HEADERS,
    )
    response.raise_for_status()
    return response


def strip_empty_values(value: Any) -> Any:
    """Recursively drop values that are empty strings or None."""
    if isinstance(value, dict):
        cleaned = {}
        for key, val in value.items():
            cleaned_val = strip_empty_values(val)
            if cleaned_val is None:
                continue
            cleaned[key] = cleaned_val
        return cleaned
    if isinstance(value, list):
        cleaned_list = [strip_empty_values(item) for item in value]
        return [item for item in cleaned_list if item is not None]
    if value == "" or value is None:
        return None
    return value


def validate_ftp_server(config: Dict[str, Any], label: str) -> Dict[str, Any]:
    """Return an FTP server configuration with only supported fields."""
    if not isinstance(config, dict):
        raise ValueError(f"-- {label} datastore ftpServer must be an object. --")
    sanitised = {key: config[key] for key in config if key in FTP_ALLOWED_KEYS}
    if "plainText" in sanitised:
        if not isinstance(sanitised["plainText"], dict):
            raise ValueError(f"-- {label} datastore ftpServer.plainText must be an object. --")
        sanitised["plainText"] = strip_empty_values(sanitised["plainText"])
    if "encrypted" in sanitised:
        if not isinstance(sanitised["encrypted"], dict):
            raise ValueError(f"-- {label} datastore ftpServer.encrypted must be an object. --")
        sanitised["encrypted"] = strip_empty_values(sanitised["encrypted"])
    sanitised = strip_empty_values(sanitised)
    if not sanitised:
        raise ValueError(f"-- {label} datastore ftpServer must include non-empty credentials. --")
    if "transferProtocol" not in sanitised:
        raise ValueError(f"-- {label} datastore ftpServer.transferProtocol is required. --")
    has_plain = "plainText" in sanitised and sanitised["plainText"]
    has_encrypted = "encrypted" in sanitised and sanitised["encrypted"]
    if not (has_plain or has_encrypted):
        raise ValueError(
            f"-- {label} datastore ftpServer must include plainText or encrypted credentials. --"
        )
    return sanitised


def validate_s3_bucket(config: Dict[str, Any], label: str) -> Dict[str, Any]:
    """Return an S3 bucket configuration with only supported fields."""
    if not isinstance(config, dict):
        raise ValueError(f"-- {label} datastore s3Bucket must be an object. --")
    sanitised = {key: config[key] for key in config if key in S3_ALLOWED_KEYS}
    sanitised = strip_empty_values(sanitised)
    if not sanitised:
        raise ValueError(f"-- {label} datastore s3Bucket must include non-empty configuration. --")
    missing = sorted(S3_ALLOWED_KEYS - set(sanitised.keys()))
    if missing:
        raise ValueError(
            f"-- {label} datastore s3Bucket is missing required fields: {', '.join(missing)}. --"
        )
    return sanitised


def load_datastore_input(raw_config: Optional[str], label: str) -> Optional[Dict[str, Any]]:
    """Return a sanitized datastore override dict or None if config is empty."""
    if raw_config is None or raw_config.strip() == "":
        return None
    try:
        parsed = json.loads(raw_config)
    except json.JSONDecodeError as exc:
        raise ValueError(f"-- Invalid JSON for {label} datastore config: {exc} --") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"-- {label} datastore config must be a JSON object. --")
    datastore_keys = [key for key in ("ftpServer", "s3Bucket") if key in parsed and parsed[key] is not None]
    if len(datastore_keys) != 1:
        raise ValueError(
            f"-- {label} datastore config must contain exactly one of ftpServer or s3Bucket. --"
        )
    datastore_key = datastore_keys[0]
    if datastore_key == "ftpServer":
        return {"ftpServer": validate_ftp_server(parsed["ftpServer"], label)}
    return {"s3Bucket": validate_s3_bucket(parsed["s3Bucket"], label)}


def replace_datastore_input(
    existing_section: Optional[Dict[str, Any]], override: Dict[str, Any]
) -> Dict[str, Any]:
    """Replace the datastore section while preserving other configuration."""
    section = copy.deepcopy(existing_section or {})
    existing_datastore_keys = [
        key for key in ("ftpServer", "s3Bucket") if key in section and section[key] is not None
    ]
    datastore_key, datastore_value = next(iter(override.items()))
    if datastore_key == "s3Bucket" and "ftpServer" in existing_datastore_keys:
        raise ValueError("-- Cannot override FTP datastore with an S3 override. --")
    if datastore_key == "ftpServer" and "s3Bucket" in existing_datastore_keys:
        raise ValueError("-- Cannot override S3 datastore with an FTP override. --")
    section.pop(datastore_key, None)
    section[datastore_key] = copy.deepcopy(datastore_value)
    return section


def transform_pipeline_payload(
    source_resource: Dict[str, Any],
    source_datastore_input: Optional[Dict[str, Any]] = None,
    target_datastore_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prepare the payload for the target pipeline."""
    transformed_resource = copy.deepcopy(source_resource)
    if 'ID' in transformed_resource:
        del transformed_resource['ID']      # remove pipeline ID
    transformed_resource["vaultID"] = TARGET_VAULT_ID
    if source_datastore_input:
        transformed_resource["source"] = replace_datastore_input(
            transformed_resource.get("source"), source_datastore_input
        )
    if target_datastore_input:
        transformed_resource["destination"] = replace_datastore_input(
            transformed_resource.get("destination"), target_datastore_input
        )
    return transformed_resource


def main(pipeline_id: str) -> None:
    """pipeline migration"""
    try:
        print("-- Initiating Pipelines migration --")
        source_datastore_input = load_datastore_input(SOURCE_DATASTORE_CONFIG, "source")
        target_datastore_input = load_datastore_input(TARGET_DATASTORE_CONFIG, "destination")
        pipeline = get_pipeline(pipeline_id)
        pipeline_name = pipeline.get("name", "Pipeline")
        print(f"-- Working on pipeline: {pipeline_name} --")

        pipeline_payload = transform_pipeline_payload(
            pipeline, source_datastore_input, target_datastore_input
        )
        create_pipeline_response = create_pipeline(pipeline_payload)

        if create_pipeline_response.status_code == 200:
            created_pipeline = create_pipeline_response.json()
            print(
                f"-- Pipeline migrated successfully: {pipeline_name}. "
                f"Source PIPELINE_ID: {pipeline.get('ID')}, "
                f"Target PIPELINE_ID: {created_pipeline.get('ID')} --"
            )
        else:
            print(
                f"-- Pipeline migration failed: {create_pipeline_response.status_code}. "
                f"{create_pipeline_response.content}"
            )
        print("-- Pipelines migration script executed successfully. --")
    except requests.exceptions.HTTPError as http_err:
        print(
            f"-- migrate_pipelines HTTP error: {http_err.response.content.decode()} --"
        )
        raise http_err
    except Exception as err:
        print(f"-- migrate_pipelines other error: {err} --")
        raise err


if __name__ == "__main__":
    if not PIPELINE_ID:
        raise ValueError("-- PIPELINE_ID is required to migrate a pipeline. --")
    main(PIPELINE_ID)
