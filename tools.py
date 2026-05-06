import json
import boto3
import requests
from typing import Optional
from langchain_core.tools import tool

from config import (
    LAMBDA_FUNCTION_NAME, API_GATEWAY_URL, AWS_REGION,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN,
    S3_BUCKET_SOURCE,
)


def _get_boto3_client(service: str):
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    if AWS_SESSION_TOKEN:
        kwargs["aws_session_token"] = AWS_SESSION_TOKEN
    return boto3.client(service, **kwargs)


def _call_lambda(payload: dict) -> dict:
    """Invokes Lambda via API Gateway (if URL configured) or directly via boto3."""
    if API_GATEWAY_URL:
        response = requests.post(API_GATEWAY_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
    else:
        client = _get_boto3_client("lambda")
        response = client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        result = json.loads(response["Payload"].read())

    # API Gateway wraps the Lambda return value in a 'body' string
    if "body" in result:
        body = result["body"]
        return json.loads(body) if isinstance(body, str) else body
    return result


@tool
def resize_rotate_flip_image_tool(
    image_name: str,
    bucket: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    rotation: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    size_preset: Optional[str] = None,
) -> str:
    """
    Resize, rotate and/or flip an image stored in Amazon S3 using AWS Lambda.
    Use this tool whenever the user wants to process, resize, rotate, or flip an image.

    Args:
        image_name: Filename of the image in S3 (e.g. 'foto1.jpg').
        bucket: S3 bucket where the image is stored. Defaults to the configured source bucket.
        width: Target width in pixels. Ignored if size_preset is provided.
        height: Target height in pixels. Ignored if size_preset is provided.
        rotation: Clockwise rotation in degrees. Accepted values: 0, 90, 180, 270.
        flip_horizontal: Mirror the image left-to-right.
        flip_vertical: Flip the image upside-down.
        size_preset: Predefined size shortcut — 'thumbnail' (150x150), 'medium' (768x768),
                     or 'large' (1024x1024). Overrides width and height when provided.
    """
    payload = {
        "bucket": bucket or S3_BUCKET_SOURCE,
        "image_name": image_name,
        "width": width,
        "height": height,
        "rotation": rotation,
        "flip_horizontal": flip_horizontal,
        "flip_vertical": flip_vertical,
        "size_preset": size_preset,
    }

    try:
        result = _call_lambda(payload)
    except requests.HTTPError as e:
        return f"HTTP error calling Lambda: {e}"
    except Exception as e:
        return f"Error invoking Lambda: {e}"

    if result.get("statusCode", 200) == 200:
        return (
            f"Image processed successfully.\n"
            f"  Output: s3://{result.get('output_bucket')}/{result.get('output_key')}\n"
            f"  Original size: {result.get('original_size')}\n"
            f"  New size: {result.get('new_size')}\n"
            f"  Rotation applied: {result.get('rotation')}°\n"
            f"  Flip horizontal: {result.get('flip_horizontal')}\n"
            f"  Flip vertical: {result.get('flip_vertical')}"
        )

    return f"Lambda returned an error: {result.get('error', 'Unknown error')}"
