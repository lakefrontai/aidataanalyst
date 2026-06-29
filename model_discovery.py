"""Fetch available Bedrock models live from the API."""

from typing import List, Dict
import boto3
from botocore.exceptions import ClientError


# Model categories to include for chat/SQL generation
_CHAT_INPUT_MODALITIES  = {"TEXT"}
_CHAT_OUTPUT_MODALITIES = {"TEXT"}


def list_bedrock_models(
    aws_key: str,
    aws_secret: str,
    aws_region: str,
    filter_text_only: bool = True,
) -> List[Dict]:
    """
    Return list of on-demand Bedrock models available in the account.
    Each dict: {model_id, provider, name, input_mod, output_mod}
    """
    client = boto3.client(
        "bedrock",
        region_name=aws_region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
    )
    try:
        resp = client.list_foundation_models(byInferenceType="ON_DEMAND")
    except ClientError as e:
        raise RuntimeError(f"Could not list models: {e}") from e

    models = []
    for m in resp.get("modelSummaries", []):
        input_mods  = set(m.get("inputModalities", []))
        output_mods = set(m.get("outputModalities", []))

        if filter_text_only:
            # Only include models that accept text input and produce text output
            if not (_CHAT_INPUT_MODALITIES & input_mods and
                    _CHAT_OUTPUT_MODALITIES & output_mods):
                continue

        models.append({
            "model_id": m["modelId"],
            "provider": m.get("providerName", "Unknown"),
            "name":     m.get("modelName", m["modelId"]),
            "input":    ", ".join(sorted(input_mods)),
            "output":   ", ".join(sorted(output_mods)),
        })

    # Sort: provider then name
    return sorted(models, key=lambda x: (x["provider"].lower(), x["name"].lower()))


def group_by_provider(models: List[Dict]) -> Dict[str, List[Dict]]:
    """Group model list by provider name."""
    groups: Dict[str, List[Dict]] = {}
    for m in models:
        groups.setdefault(m["provider"], []).append(m)
    return groups


def embedding_models(models: List[Dict]) -> List[Dict]:
    """Filter to models likely usable for embeddings (Titan Embed, Cohere Embed)."""
    keywords = ("embed",)
    return [m for m in models if any(k in m["model_id"].lower() for k in keywords)]


def list_model_ids(aws_key: str, aws_secret: str, aws_region: str) -> List[str]:
    """Convenience — return just model_id strings."""
    return [m["model_id"] for m in list_bedrock_models(aws_key, aws_secret, aws_region)]
