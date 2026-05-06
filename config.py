import os
from dotenv import load_dotenv

load_dotenv()

# AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

# S3
S3_BUCKET_SOURCE = os.getenv("S3_BUCKET_SOURCE", "ai-image-lab-source")
S3_BUCKET_DEST = os.getenv("S3_BUCKET_DEST", S3_BUCKET_SOURCE)

# Lambda / API Gateway
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "ImageResizeAgent")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "")

# Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))

# Preset sizes
SIZE_PRESETS = {
    "thumbnail": (150, 150),
    "medium": (768, 768),
    "large": (1024, 1024),
}
