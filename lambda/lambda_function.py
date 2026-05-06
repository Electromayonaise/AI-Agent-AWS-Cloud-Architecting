import json
import logging
import boto3
from io import BytesIO
from PIL import Image

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

SIZE_PRESETS = {
    "thumbnail": (150, 150),
    "medium": (768, 768),
    "large": (1024, 1024),
}

FORMAT_MAP = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
}

FOLDER_MAP = {
    "thumbnail": "thumbnails",
    "medium": "medium",
    "large": "large",
}


def _pil_format(image_name: str) -> str:
    ext = image_name.rsplit(".", 1)[-1].lower()
    return FORMAT_MAP.get(ext, "JPEG")


def _content_type(pil_format: str) -> str:
    return "image/png" if pil_format == "PNG" else "image/jpeg"


def process_image(
    bucket: str,
    image_name: str,
    width=None,
    height=None,
    rotation: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    size_preset: str = None,
    dest_bucket: str = None,
) -> dict:
    logger.info(f"Processing: s3://{bucket}/{image_name} | preset={size_preset} | "
                f"size={width}x{height} | rotation={rotation} | "
                f"flip_h={flip_horizontal} | flip_v={flip_vertical}")

    # Download from S3
    response = s3_client.get_object(Bucket=bucket, Key=image_name)
    image = Image.open(BytesIO(response["Body"].read()))
    original_size = image.size
    pil_format = _pil_format(image_name)

    # JPEG cannot store transparency — convert before any operation
    if pil_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGB")

    # Determine output size and destination folder
    if size_preset and size_preset in SIZE_PRESETS:
        width, height = SIZE_PRESETS[size_preset]
        folder = FOLDER_MAP[size_preset]
    elif width and height:
        width, height = int(width), int(height)
        folder = "custom"
    else:
        width, height = SIZE_PRESETS["thumbnail"]
        folder = "thumbnails"

    # Resize
    processed = image.resize((width, height), Image.LANCZOS)

    # Rotate (clockwise: negate for PIL which is counter-clockwise)
    rotation = int(rotation) if rotation else 0
    if rotation:
        processed = processed.rotate(-rotation, expand=False)

    # Flip
    if flip_horizontal:
        processed = processed.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_vertical:
        processed = processed.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    # Save to buffer
    buffer = BytesIO()
    processed.save(buffer, format=pil_format)
    buffer.seek(0)

    # Build output key preserving only the base filename (strips any sub-path)
    base_name = image_name.rsplit("/", 1)[-1]
    output_key = f"{folder}/{base_name}"
    dest_bucket = dest_bucket or bucket

    s3_client.put_object(
        Bucket=dest_bucket,
        Key=output_key,
        Body=buffer,
        ContentType=_content_type(pil_format),
    )

    logger.info(f"Saved to s3://{dest_bucket}/{output_key}")

    return {
        "statusCode": 200,
        "output_bucket": dest_bucket,
        "output_key": output_key,
        "original_size": list(original_size),
        "new_size": [width, height],
        "rotation": rotation,
        "flip_horizontal": flip_horizontal,
        "flip_vertical": flip_vertical,
        "message": f"Image processed: s3://{dest_bucket}/{output_key}",
    }


def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # --- Path 1: S3 event trigger ---
        if "Records" in event:
            bucket = event["Records"][0]["s3"]["bucket"]["name"]
            key = event["Records"][0]["s3"]["object"]["key"]

            # Skip already-processed images to avoid infinite loops
            if any(key.startswith(f"{f}/") for f in FOLDER_MAP.values()):
                logger.info(f"Skipping already-processed key: {key}")
                return {"statusCode": 200, "body": json.dumps({"message": "Skipped"})}

            results = []
            for preset in SIZE_PRESETS:
                results.append(process_image(bucket=bucket, image_name=key, size_preset=preset))

            return {
                "statusCode": 200,
                "body": json.dumps({"message": "All presets generated", "results": results}),
            }

        # --- Path 2: API Gateway (body is a JSON string) ---
        if "body" in event:
            body = event["body"]
            params = json.loads(body) if isinstance(body, str) else body
        # --- Path 3: Direct boto3 invocation ---
        else:
            params = event

        result = process_image(
            bucket=params["bucket"],
            image_name=params["image_name"],
            width=params.get("width"),
            height=params.get("height"),
            rotation=params.get("rotation", 0),
            flip_horizontal=params.get("flip_horizontal", False),
            flip_vertical=params.get("flip_vertical", False),
            size_preset=params.get("size_preset"),
            dest_bucket=params.get("dest_bucket"),
        )

        return {"statusCode": 200, "body": json.dumps(result)}

    except KeyError as e:
        logger.error(f"Missing parameter: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": f"Missing parameter: {e}"})}
    except Exception as e:
        logger.exception("Unhandled error")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
