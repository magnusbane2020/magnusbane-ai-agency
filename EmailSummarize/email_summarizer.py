import os
import sys
import time
import pathlib
from typing import Optional
from dataclasses import dataclass
from openai import OpenAI

# ---- pricing for gpt-4o-mini (USD/token) ----
INPUT_PER_TOKEN  = 0.15 / 1_000_000
OUTPUT_PER_TOKEN = 0.60 / 1_000_000

MODEL = "gpt-4o-mini"

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

def estimate_cost(u: Usage) -> float:
    return u.prompt_tokens * INPUT_PER_TOKEN + u.completion_tokens * OUTPUT_PER_TOKEN

PROMPT_SYSTEM = (
    "You are an AI assistant for Magnusbane that summarizes business emails for busy teams. "
    "Output must be concise, client-ready, and actionable."
)

PROMPT_USER = """Summarize the email below into:
1) Summary: 3–5 bullets.
2) Action items: bullet list with [Owner?] [Due date?] [Blocking dependencies?]. If unknown, mark as TBC.
3) Priority: High/Medium/Low + 1‑line reason.
4) Suggested reply: short, polite, professional.

The email content:
---
{email_text}
---
If the text contains multiple emails in a thread, summarize the latest AND include context from prior messages.
"""

def summarize_text(client: OpenAI, text: str) -> tuple[str, Usage]:
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": PROMPT_USER.format(email_text=text.strip())},
        ],
    )
    content = resp.choices[0].message.content.strip()
    usage = Usage(
        prompt_tokens=getattr(resp.usage, "prompt_tokens", 0),
        completion_tokens=getattr(resp.usage, "completion_tokens", 0),
        total_tokens=getattr(resp.usage, "total_tokens", 0),
    )
    return content, usage

def save_markdown(base_name: str, text: str, usage: Usage, cost: float) -> str:
    ts = time.strftime("%Y%m%d-%H%M")
    outdir = pathlib.Path("outputs"); outdir.mkdir(exist_ok=True, parents=True)
    safe = "".join(c for c in base_name if c.isalnum() or c in "-_ ").strip().replace(" ", "-").lower()
    path = outdir / f"{safe or 'email'}-summary-{ts}.md"
    md = []
    md.append(f"# Email Summary — {base_name}\n")
    md.append(text)
    md.append("\n---")
    md.append(f"\n_Tokens: prompt {usage.prompt_tokens}, completion {usage.completion_tokens}, "
              f"total {usage.total_tokens} • Est. cost: ${cost:.6f} on {MODEL}_\n")
    path.write_text("\n".join(md), encoding="utf-8")
    return str(path)

def read_input(path: Optional[str]) -> tuple[str, str]:
    """Returns (base_name_for_output, email_text)."""
    if path:
        p = pathlib.Path(path)
        if not p.exists():
            raise SystemExit(f"File not found: {p}")
        return (p.stem, p.read_text(encoding="utf-8", errors="ignore"))
    # Fallback: let user paste text
    print("\nPaste the email text below. Finish with an empty line (press Enter twice):\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "" and lines and lines[-1].strip() == "":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        raise SystemExit("No text provided.")
    return ("pasted-email", text)

def main():
    if "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("Missing OPENAI_API_KEY. Put it in your environment or a .env file.")

    client = OpenAI()
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None

    base, email_text = read_input(file_arg)
    print(f"\n=== Summarizing: {base} ===\n")

    summary, usage = summarize_text(client, email_text)
    print(summary)

    cost = estimate_cost(usage)
    out_path = save_markdown(base, summary, usage, cost)
    print(f"\nSaved → {out_path}")
    print(f"Estimated cost: ${cost:.6f} (model: {MODEL})\n")

if __name__ == "__main__":
    main()
