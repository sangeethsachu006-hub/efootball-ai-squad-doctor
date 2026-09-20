import json
import os
import asyncio

from google import genai
from google.genai import types

PROMPT = """
You are the image-recognition module for an eFootball squad analysis bot.

Inspect the supplied eFootball squad screenshot carefully. Extract ONLY information that is visibly supported.
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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    model = os.getenv("VISION_MODEL", "gemini-2.5-flash-lite")
    client = genai.Client(api_key=api_key)

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg",
    )

    def call_model():
        return client.models.generate_content(
            model=model,
            contents=[PROMPT, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=1200,
            ),
        )

    response = await asyncio.to_thread(call_model)
    raw = (response.text or "").strip()

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
