import os
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
    "Output must be concise, client-ready, and actionable."
)

PROMPT_USER = """Summarize the email below into:
1) Summary: 3–5 bullets.
2) Action items: bullet list with [Owner?] [Due date?] [Blocking dependencies?]. If unknown, mark as TBC.
3) Priority: High/Medium/Low + 1‑line reason.
4) Suggested reply: short, polite, professional.

Email:
---
{email_text}
---
"""

app = FastAPI(title="Magnusbane Email Summarizer API")

class SummarizeRequest(BaseModel):
    text: str

@app.post("/summarize")
def summarize(req: SummarizeRequest):
    if "OPENAI_API_KEY" not in os.environ:
        return JSONResponse({"error": "Missing OPENAI_API_KEY"}, status_code=500)

    client = OpenAI()
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": PROMPT_USER.format(email_text=req.text.strip())},
        ],
    )
    content = resp.choices[0].message.content.strip()
    usage = getattr(resp, "usage", None)
    data = {
        "summary_markdown": content,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        },
        "model": MODEL,
    }
    return data
