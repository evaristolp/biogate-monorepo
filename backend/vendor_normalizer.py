import anthropic
import json
import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv

# Load .env from project root (parent of backend/) so it works from any cwd
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

import anthropic
import json
import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv

# Load .env from project root (parent of backend/) so it works from any cwd
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

_api_key = os.getenv("ANTHROPIC_API_KEY")
if not _api_key or not _api_key.strip():
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. Add it to .env in the project root or set the environment variable."
    )
client = anthropic.Anthropic(api_key=_api_key.strip())

NORMALIZATION_PROMPT = """You are a biotech supply chain analyst. Given a list of vendor names from a biotechnology company's procurement records, return a JSON array where each element contains:

- "raw_name": the original input name (unchanged)
- "normalized_name": the canonical company name (e.g., "BGI Research" → "BGI Genomics Co., Ltd.")
- "country_hint": ISO 3166-1 alpha-2 country code of headquarters (e.g., "CN", "US"), or null if unknown
- "parent_company_hint": the ultimate parent company name if this is a subsidiary/brand/division, or null
- "equipment_type_hint": one of ["sequencing", "reagents", "instruments", "consumables", "software", "services", "other"], or null

Respond ONLY with valid JSON. No markdown, no explanation."""


async def normalize_vendors(vendor_names: List[str]) -> List[Dict]:
    """Batch normalize vendor names via Claude API."""
    if not vendor_names:
        return []

    vendor_list = "\n".join(f"- {name}" for name in vendor_names)

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"Normalize these biotech vendors:\n{vendor_list}"
        }],
        system=NORMALIZATION_PROMPT
    )

    raw_text = message.content[0].text
    # Strip markdown fences if present
    cleaned = raw_text.strip().removeprefix("```json").removesuffix("```").strip()

    return json.loads(cleaned)
