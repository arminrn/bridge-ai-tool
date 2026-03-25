
import os
import re
import io
import json
import asyncio
import pandas as pd

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

# Create FastAPI app
app = FastAPI(title="Bridge Inspection AI Tool")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Clean text function
# ---------------------------
def clean_text(text):
    text = str(text)
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    text = re.sub(r"\@\w+|\#", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ---------------------------
# GPT extraction function
# ---------------------------
async def extract_bridge_info(report_text, semaphore):
    async with semaphore:
        prompt = f"""
You are a structural engineer.

Determine if this bridge needs replacement.

Rules:
- Answer "yes" only if replacement is clearly needed.
- Otherwise answer "no".

Return ONLY valid JSON:

{{
  "bridge_replacement_required": "yes or no",
  "confidence": "high, medium, low"
}}

Text:
{report_text}
"""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            return json.loads(result)

        except Exception:
            return {
                "bridge_replacement_required": None,
                "confidence": None
            }

# ---------------------------
# Batch processing
# ---------------------------
async def run_batches(texts, batch_size=20, max_concurrent=10):
    semaphore = asyncio.Semaphore(max_concurrent)
    all_results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        tasks = [extract_bridge_info(t, semaphore) for t in batch]
        results = await asyncio.gather(*tasks)
        all_results.extend(results)

    return all_results

# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def home():
    return {"message": "Bridge Inspection AI Backend is running"}

@app.post("/analyze/")
async def analyze(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        if "REMARKS" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain REMARKS column")

        df = df.dropna(subset=["REMARKS"])
        df["processed"] = df["REMARKS"].apply(clean_text)

        texts = df["processed"].tolist()

        results = await run_batches(texts)

        results_df = pd.DataFrame(results)
        df_final = pd.concat([df.reset_index(drop=True), results_df], axis=1)

        output = io.StringIO()
        df_final.to_csv(output, index=False)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=results.csv"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
