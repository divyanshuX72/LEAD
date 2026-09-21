from __future__ import annotations

import json
import re

from pydantic import BaseModel

from platform_app.config.settings import get_settings


class GeneratedStrategy(BaseModel):
    keywords: list[str]
    business_categories: list[str] = []


class SearchStrategyEngine:
    """
    ATREAL-specific discovery strategy.

    The agent's target customer is fixed by ATREAL's current
    company configuration: Real Estate Developers.
    """

    def __init__(self):
        self.settings = get_settings()

    @staticmethod
    def _clean_keywords(keywords: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for keyword in keywords:
            cleaned = re.sub(r"\s+", " ", keyword.strip())

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key in seen:
                continue

            seen.add(key)
            result.append(cleaned)

        return result

    def _get_client(self):
        if not self.settings.GEMINI_API_KEY:
            return None

        from google import genai

        return genai.Client(
            api_key=self.settings.GEMINI_API_KEY
        )

    async def generate_strategy(
        self,
        keywords: list[str],
        location: str,
    ) -> GeneratedStrategy:

        base_keywords = self._clean_keywords(keywords)

        client = self._get_client()

        if not client:
            return self._fallback_strategy(base_keywords)

        prompt = f"""
You are the lead discovery strategist for ATREAL STUDIOS PRIVATE LIMITED.

ATREAL product:
ATREAL Immersia — VR-based immersive real estate walkthrough platform.

ATREAL target customer:
Real Estate Developers.

ATREAL business model:
B2B.

The user wants to discover prospective real-estate developer businesses
in this location:

{location}

User supplied discovery terms:
{json.dumps(base_keywords)}

Generate search terms that find REAL ESTATE DEVELOPERS and property
development companies.

Rules:

1. Stay strictly within real-estate development.
2. Do not search for unrelated real-estate service providers such as:
   brokers, agents, interior designers, architects, contractors,
   property managers, mortgage companies, or listing portals unless
   the business is itself clearly a property developer.
3. Use several discovery angles:
   - real estate developer
   - property developer
   - residential developer
   - commercial developer
   - real estate development company
   - builder/developer where appropriate
   - project-focused developer searches
4. Preserve useful user-supplied terms.
5. Do not add the location into the keyword itself.
6. Avoid duplicate or near-duplicate terms.
7. Prefer terms that identify actual businesses rather than properties.
8. Return 8-15 search terms.

Return only JSON:

{{
  "keywords": ["..."],
  "business_categories": ["real estate developer"]
}}
"""

        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )

            if not response.text:
                return self._fallback_strategy(base_keywords)

            data = json.loads(response.text)

            generated = self._clean_keywords(
                data.get("keywords", [])
            )

            combined = self._clean_keywords(
                base_keywords + generated
            )

            return GeneratedStrategy(
                keywords=combined[:20],
                business_categories=[
                    "real estate developer"
                ],
            )

        except Exception as exc:
            print(
                f"[Strategy] Gemini strategy failed: {exc}"
            )

            return self._fallback_strategy(base_keywords)

    def _fallback_strategy(
        self,
        base_keywords: list[str],
    ) -> GeneratedStrategy:

        additions = [
            "real estate developer",
            "property developer",
            "real estate development company",
            "residential property developer",
            "commercial property developer",
            "residential developer",
            "commercial developer",
            "real estate builder developer",
            "property development company",
            "real estate projects developer",
        ]

        keywords = self._clean_keywords(
            base_keywords + additions
        )

        return GeneratedStrategy(
            keywords=keywords[:20],
            business_categories=[
                "real estate developer"
            ],
        )