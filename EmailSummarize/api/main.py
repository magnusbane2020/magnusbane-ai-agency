import os
from typing import Optional, List
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from fastapi.responses import JSONResponse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MODEL = "gpt-4o-mini"

PROMPT_SYSTEM = (
    "You are an AI assistant for Magnusbane that summarizes business emails for busy teams. "
    "Output must be concise, client-ready, and actionable. "
    "Priority rules: HIGH if urgency or date within 3 days (e.g., 'urgent', 'ASAP', 'deadline', "
    "'refund', 'complaint', 'invoice overdue', or explicit dates within 3 days); "
    "MEDIUM for routine tasks with dates >3 days; LOW for FYI/no action."
)

PROMPT_USER = """Summarize the email below into:
1) Summary: 3–5 bullets.
2) Action items: bullet list with [Owner?] [Due date?] [Blocking dependencies?]. If unknown, mark as TBC.
3) Priority: High/Medium/Low + 1-line reason.
4) Suggested reply: short, polite, professional.

Email:
---
{email_text}
---
"""

app = FastAPI(title="Magnusbane Email Summarizer API")

class SummarizeRequest(BaseModel):
    text: str
    lang: Optional[str] = None  # e.g., "English" or "Romanian"

class BatchItem(BaseModel):
    text: str
    lang: Optional[str] = None

class BatchRequest(BaseModel):
    items: List[BatchItem]

def summarize_core(client: OpenAI, text: str, lang: Optional[str]) -> dict:
    lang_hint = f"\nPlease write the entire output in {lang}." if lang else ""
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": PROMPT_USER.format(email_text=text.strip()) + lang_hint},
        ],
    )
    content = resp.choices[0].message.content.strip()
    usage = getattr(resp, "usage", None)
    return {
        "summary_markdown": content,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        },
        "model": MODEL,
    }

@app.post("/summarize")
def summarize(req: SummarizeRequest):
    if "OPENAI_API_KEY" not in os.environ:
        return JSONResponse({"error": "Missing OPENAI_API_KEY"}, status_code=500)
    client = OpenAI()
    return summarize_core(client, req.text, req.lang)

@app.post("/summarize-batch")
def summarize_batch(req: BatchRequest):
    if "OPENAI_API_KEY" not in os.environ:
        return JSONResponse({"error": "Missing OPENAI_API_KEY"}, status_code=500)
    client = OpenAI()
    results = [summarize_core(client, item.text, item.lang) for item in req.items]
    return {"results": results, "count": len(results), "model": MODEL}
