"""
Claude-powered vendor name normalization for BioGate audit pipeline.

Batch normalizes vendor names to structured JSON: normalized_name, country_hint,
parent_company_hint, equipment_type_hint. Uses Anthropic API; multiple vendors per
call to limit cost (batch normalization). Requires ANTHROPIC_API_KEY in env.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# Batch size to stay under context limits and control cost
# Week 3 requirement: batch up to ~20 vendors per call.
BATCH_SIZE = 20


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from model output, handling markdown code blocks."""
    text = (text or "").strip()
    # Strip optional markdown code block
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "vendors" in data:
            return data["vendors"]
        return []
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse Claude JSON: %s", e)
        return []


async def normalize_vendors(raw_names: list[str]) -> list[dict[str, Any]]:
    """
    Batch-normalize vendor names via Claude. Returns list of dicts with keys:
    raw_name, normalized_name, country_hint, parent_company_hint, equipment_type_hint.
    Also strips non-essential noise (e.g. PO numbers, invoice text) and fixes obvious typos.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set; skipping Claude normalization")
        return []

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("anthropic package not installed")
        return []

    client = AsyncAnthropic(api_key=api_key)
    all_results: list[dict[str, Any]] = []

    for i in range(0, len(raw_names), BATCH_SIZE):
        batch = raw_names[i : i + BATCH_SIZE]
        prompt = """Normalize each of the following vendor/supplier fields (often messy text from POs, invoices, PDFs, or spreadsheets).
For each input, first extract the *company name* and discard non-essential noise like:
- PO numbers (e.g. "PO# 1234"), invoice numbers, internal IDs
- "Attn", contact names, email addresses, phone numbers
- Free-form comments or notes

Then return:
- normalized_name: canonical company name (fix obvious typos, expand common abbreviations like Inc, Ltd, Co).
- country_hint: ISO country or region if inferrable, else null.
- parent_company_hint: ultimate parent company if this is a subsidiary (e.g. "Complete Genomics" -> "BGI Group"), else null.
- equipment_type_hint: brief category like "sequencing", "reagents", "lab equipment", or null.

Return a JSON array of objects with keys: raw_name, normalized_name, country_hint, parent_company_hint, equipment_type_hint.
One object per input name, in the same order. Use null for unknown.

Vendor fields (one per line):
"""
        prompt += "\n".join(f"- {n!r}" for n in batch)

        try:
            msg = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            content = msg.content
            if isinstance(content, list) and content:
                block = content[0]
                if getattr(block, "text", None):
                    text = block.text
                else:
                    text = str(block)
            else:
                text = str(content) if content else ""

            items = _extract_json_array(text)
            for j, name in enumerate(batch):
                row = items[j] if j < len(items) else {}
                if not isinstance(row, dict):
                    row = {}
                all_results.append({
                    "raw_name": name,
                    "normalized_name": (row.get("normalized_name") or "").strip() or None,
                    "country_hint": (row.get("country_hint") or "").strip() or None,
                    "parent_company_hint": (row.get("parent_company_hint") or "").strip() or None,
                    "equipment_type_hint": (row.get("equipment_type_hint") or "").strip() or None,
                })
        except Exception as e:
            logger.warning("Claude batch failed for names %s: %s", batch[:3], e)
            for name in batch:
                all_results.append({
                    "raw_name": name,
                    "normalized_name": None,
                    "country_hint": None,
                    "parent_company_hint": None,
                    "equipment_type_hint": None,
                })

    return all_results
