import os
import sys
import time
import pathlib
from openai import OpenAI

# ==== Pricing settings (USD per 1 token) for gpt-4o-mini ====
# OpenAI lists: $0.15 / 1M input tokens, $0.60 / 1M output tokens
INPUT_PER_TOKEN  = 0.15 / 1_000_000
OUTPUT_PER_TOKEN = 0.60 / 1_000_000
MODEL = "gpt-4o-mini"

def sanitize_filename(text: str) -> str:
    keep = "-_() "
    return "".join(c for c in text if c.isalnum() or c in keep).strip().replace(" ", "-").lower()

def agency_ideas_for(client: OpenAI, niche: str) -> tuple[str, dict]:
    system = (
        "You are an AI automation consultant for Magnusbane. "
        "Propose scrappy, realistic 1-week builds using Zapier/Make + OpenAI. "
        "Each idea must include: Title, Tools, 5 concrete Steps, Business Value (ROI/time saved). "
        "Be specific; no fluff."
    )
    user = f"Business niche: {niche}. Generate exactly 3 ideas."

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.3,
    )
    content = resp.choices[0].message.content.strip()
    usage = {
        "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
        "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
        "total_tokens": getattr(resp.usage, "total_tokens", 0),
    }
    return content, usage

def estimate_cost(usage: dict) -> float:
    return usage["prompt_tokens"] * INPUT_PER_TOKEN + usage["completion_tokens"] * OUTPUT_PER_TOKEN

def save_markdown(niche: str, ideas_text: str, usage: dict, cost: float) -> str:
    ts = time.strftime("%Y%m%d-%H%M")
    outdir = pathlib.Path("outputs"); outdir.mkdir(exist_ok=True)
    fname = f"{sanitize_filename(niche)}-{ts}.md"
    path = outdir / fname
    md = []
    md.append(f"# Magnusbane – 1‑Week Automation Ideas for **{niche}**\n")
    md.append(ideas_text)
    md.append("\n---\n")
    md.append(f"_Tokens: prompt {usage['prompt_tokens']}, completion {usage['completion_tokens']}, "
              f"total {usage['total_tokens']} • Est. cost: ${cost:.6f} on {MODEL}_\n")
    path.write_text("\n".join(md), encoding="utf-8")
    return str(path)

def main():
    if "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("Missing OPENAI_API_KEY. Set it and re-run.")

    client = OpenAI()

    # Ask user to type niche
    niche = input("Enter the business niche (e.g., dentist, real estate agency): ").strip()
    if not niche:
        niche = "local business"

    print(f"\n=== Magnusbane: 1-Week Automation Ideas for: {niche} ===\n")
    ideas_text, usage = agency_ideas_for(client, niche)
    print(ideas_text)

    cost = estimate_cost(usage)
    out_path = save_markdown(niche, ideas_text, usage, cost)
    print(f"\n---\nTokens → prompt: {usage['prompt_tokens']}, completion: {usage['completion_tokens']}, total: {usage['total_tokens']}")
    print(f"Estimated cost (gpt-4o-mini): ${cost:.6f}")
    print(f"Saved to: {out_path}\n")
    print("(✅ Day 1.5 complete: persisted output + cost tracking.)\n")

if __name__ == "__main__":
    main()
