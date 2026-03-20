import os, json, requests, time

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
URL = "https://api.openai.com/v1/responses"
MODEL = "gpt-5-mini"

# pricing (USD per token)
INPUT_COST = 0.25 / 1_000_000
OUTPUT_COST = 2.00 / 1_000_000


def call_openai_json(prompt: str, max_retries=5):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": "Return valid JSON only."}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    }

    for attempt in range(max_retries):
        r = requests.post(URL, headers=headers, json=payload)

        if r.status_code == 200:
            break

        if r.status_code == 429:
            wait = 2 ** attempt
            time.sleep(wait)
            continue

        r.raise_for_status()
    else:
        raise RuntimeError("OpenAI API failed after retries")

    response_json = r.json()

    # Extract text
    text = ""

    for item in response_json.get("output", []):
        contents = item.get("content", [])
        for c in contents:
            if c.get("type") == "output_text":
                text += c.get("text", "")

    if not text:
        text = response_json.get("output_text", "")

    if not text.strip():
        raise RuntimeError("No text returned from OpenAI")

    parsed = json.loads(text)

    # Extract usage
    usage = response_json.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    cost = (
        input_tokens * INPUT_COST +
        output_tokens * OUTPUT_COST
    )

    return parsed, {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost
    }