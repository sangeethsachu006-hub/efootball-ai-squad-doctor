import base64
import json
import os
from openai import AsyncOpenAI

PROMPT = """
You are the image-recognition module for an eFootball squad analysis bot.

Inspect the supplied eFootball screenshot carefully. Extract ONLY information that is visibly supported.
Do not invent player names, ratings, positions, playstyles, formation or tactics.

Return valid JSON with exactly these keys:
{
  "formation": "string or Unknown",
  "playstyle": "string or Unknown",
  "players": [
    {
      "name": "visible player name or Unknown",
      "position": "visible position or Unknown",
      "playstyle": "visible playing style or Unknown"
    }
  ],
  "notes": ["short notes about visibility/uncertainty"]
}

If the screenshot is not a squad screen, return an empty players list and explain in notes.
"""

async def analyze_squad_image(image_bytes: bytes) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    model = os.getenv("VISION_MODEL", "gpt-5.6-luna")
    client = AsyncOpenAI(api_key=api_key)

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = await client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{b64}",
                    },
                ],
            }
        ],
    )

    raw = response.output_text.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("Vision model returned invalid JSON.")

    data.setdefault("formation", "Unknown")
    data.setdefault("playstyle", "Unknown")
    data.setdefault("players", [])
    data.setdefault("notes", [])

    return data
