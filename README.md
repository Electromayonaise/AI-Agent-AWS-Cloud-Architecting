# AI Image Processing Agent — AWS

An AI agent built with LangChain + Gemini that resizes, rotates, and flips images stored in Amazon S3 by invoking an AWS Lambda function.

## Architecture

```
User prompt → Gemini LLM → LangChain Agent → resize_rotate_flip_image_tool
    → API Gateway (or boto3) → Lambda → Pillow → S3 (output)
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
- Google AI Studio API key (free): https://aistudio.google.com
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

1. Go to **AWS Lambda → Create function**
2. Settings:
   - **Name:** `ImageResizeAgent`
   - **Runtime:** Python 3.12
   - **Role:** `LabRole`
3. Paste the contents of `lambda/lambda_function.py` into the inline editor
4. **Add Pillow layer** (Pillow is not in the Lambda runtime):
   - Go to **Layers → Add a layer → Specify an ARN**
   - Use the KLayers ARN for Python 3.12 + Pillow in us-east-1:
     `arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-Pillow:4`
   - (Check latest version at https://github.com/keithrozario/Klayers)
5. Increase **timeout** to 30 s (Configuration → General configuration)
6. Set **memory** to 256 MB

### 3 — Configure S3 trigger (auto-resize on upload)

1. Open the Lambda function → **Add trigger**
2. Select **S3**
3. Bucket: `ai-image-lab-source`
4. Event type: `PUT`
5. Save

> This triggers Lambda automatically whenever you upload a new image, generating thumbnail, medium, and large versions.

### 4 — Create API Gateway endpoint (for agent invocation)

1. Go to **Amazon API Gateway → Create API → HTTP API**
2. **Name:** `ImageAgentAPI`
3. Add integration: **Lambda → ImageResizeAgent**
4. Route: `POST /resize`
5. **Deploy stage:** `prod`
6. Copy the generated URL — it looks like:
   `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/resize`
7. Paste it into your `.env` as `API_GATEWAY_URL`

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
| `GOOGLE_API_KEY` | https://aistudio.google.com → Get API key |
| `AWS_ACCESS_KEY_ID` | AWS Academy Learner Lab → AWS Details |
| `AWS_SECRET_ACCESS_KEY` | AWS Academy Learner Lab → AWS Details |
| `AWS_SESSION_TOKEN` | AWS Academy Learner Lab → AWS Details |
| `S3_BUCKET_SOURCE` | The bucket you created in Step 1 |
| `API_GATEWAY_URL` | The URL from Step 4 (leave blank to use boto3 direct) |

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
