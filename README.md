# AI Image Processing Agent — AWS

An AI agent built with LangChain + Groq (Llama 3.3) that resizes, rotates, and flips images stored in Amazon S3 by invoking an AWS Lambda function.

## Architecture

```
User prompt → Groq LLM (Llama 3.3) → LangChain Agent → resize_rotate_flip_image_tool
    → boto3 → Lambda → Pillow → S3 (output)
```

## Project structure

```
├── agent.py               # Agent entry point
├── tools.py               # LangChain tool that calls Lambda
├── config.py              # Centralised configuration
├── lambda/
│   └── lambda_function.py # Code to deploy to AWS Lambda
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.10+
- Groq API key (free): https://console.groq.com
- AWS Academy Learner Lab access

---

## AWS Setup

### 1 — Create the S3 bucket

1. Go to **Amazon S3 → Create bucket**
2. Name: `ai-image-lab-source` (or your choice)
3. Region: `us-east-1`
4. Keep all other defaults

Upload at least one large image (≥ 1280×1280) to test.

### 2 — Create the Lambda function

1. Go to **AWS Lambda → Create function → Author from scratch**
2. Settings:
   - **Name:** `ImageResizeAgent`
   - **Runtime:** Python 3.12
   - **Permissions:** expand "Change default execution role" → **Use an existing role** → select `lambda-run-role`
3. Click **Create function**, then in the **Code** tab paste the contents of `lambda/lambda_function.py` and click **Deploy**
4. **Add Pillow layer** — Pillow is not available in the Lambda runtime and must be added as a layer built for the correct platform. From **CloudShell**:

```bash
mkdir -p python
pip install pillow \
  --platform manylinux2014_x86_64 \
  --target python/ \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade
zip -r pillow-layer.zip python/
aws lambda publish-layer-version \
  --layer-name pillow-layer \
  --zip-file fileb://pillow-layer.zip \
  --compatible-runtimes python3.12

# Get the ARN of the new layer
aws lambda list-layer-versions --layer-name pillow-layer \
  --query 'LayerVersions[0].LayerVersionArn' --output text
```

Then in Lambda → **ImageResizeAgent → Layers → Add a layer → Specify an ARN** → paste the ARN → **Add**.

> **Note:** Using `--platform manylinux2014_x86_64` is required. A plain `pip install pillow` in CloudShell produces binaries incompatible with the Lambda runtime (`_imaging` import error).

5. Increase **timeout** to 30 s → Configuration → General configuration
6. Set **memory** to 256 MB

### 3 — Configure S3 trigger (auto-resize on upload)

1. Open the Lambda function → **Add trigger**
2. Select **S3**
3. Bucket: `ai-image-lab-source`
4. Event type: `PUT`
5. Save

> This triggers Lambda automatically whenever you upload a new image, generating thumbnail, medium, and large versions.

### 4 — API Gateway (optional)

AWS Academy restricts `apigateway:PUT`, so API Gateway creation via the console will fail. The agent calls Lambda **directly via boto3** by default (leave `API_GATEWAY_URL` empty in `.env`). If your environment does allow API Gateway, set up a `POST /resize` route pointing to `ImageResizeAgent` and paste the URL into `.env`.

### 5 — Verify CloudWatch logs

Lambda logs are automatically sent to CloudWatch.
Go to **CloudWatch → Log groups → /aws/lambda/ImageResizeAgent** to monitor execution.

---

## Local Setup

```bash
# 1. Clone / download the project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your keys (see below)

# 4. Run the agent
python agent.py
```

### .env values

| Variable | Where to get it |
|---|---|
| `GROQ_API_KEY` | https://console.groq.com → API Keys → Create |
| `AWS_ACCESS_KEY_ID` | AWS Academy Learner Lab → AWS Details |
| `AWS_SECRET_ACCESS_KEY` | AWS Academy Learner Lab → AWS Details |
| `AWS_SESSION_TOKEN` | AWS Academy Learner Lab → AWS Details → Show (AWS CLI block) |
| `S3_BUCKET_SOURCE` | The bucket name created in Step 1 |
| `API_GATEWAY_URL` | Leave blank to use boto3 direct invocation |

> **AWS Academy note:** credentials expire when the lab session ends. Paste fresh credentials from "AWS Details" each time you restart the lab.

---

## Example prompts

```
Redimensiona la imagen foto1.jpg a 256x256 en el bucket ai-image-lab-source
Reduce la imagen paisaje.png a tamaño thumbnail y rota 90°
Quiero una versión miniatura de selfie.jpg rotada 180 grados
Resize and rotate image foto1.jpg to 768x768 and 270° in bucket ai-image-lab-source
Voltea horizontalmente la imagen logo.png y guárdala como medium
```

## Output folder structure in S3

| Preset | Folder | Resolution |
|---|---|---|
| thumbnail | `thumbnails/` | 150 × 150 |
| medium | `medium/` | 768 × 768 |
| large | `large/` | 1024 × 1024 |
| custom | `custom/` | user-defined |

---

## Supported image formats

JPG, JPEG, PNG
