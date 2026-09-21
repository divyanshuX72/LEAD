"""
Search Strategy Engine — Enhanced Keyword Expansion

Uses Gemini to expand keywords for broader lead discovery.
Generates 8-12 diverse keywords per base keyword.
Supports additional keyword generation when initial results run dry.
"""

import json
from pydantic import BaseModel
from platform_app.config.settings import get_settings


class GeneratedStrategy(BaseModel):
    keywords: list[str]
    business_categories: list[str] = []


class SearchStrategyEngine:
    def __init__(self):
        self.settings = get_settings()

    def _get_client(self):
        if not self.settings.GEMINI_API_KEY:
            return None
        from google import genai
        return genai.Client(api_key=self.settings.GEMINI_API_KEY)

    async def generate_strategy(
        self,
        keyword: str,
        location: str | None = None,
    ) -> GeneratedStrategy | None:
        """Expand a keyword into 8-12 related search terms using Gemini."""

        client = self._get_client()
        if not client:
            return self._fallback_strategy(keyword)

        loc_context = f' in "{location}"' if location else ""

        prompt = f"""You are an expert B2B lead generation specialist. Given the base keyword "{keyword}"{loc_context}, generate a comprehensive list of 8-12 high-quality, DIVERSE business search keywords that will help find maximum unique businesses.

Rules:
- Generate keywords across ALL these categories:
  1. EXACT MATCH: The keyword itself (e.g., "{keyword}")
  2. ROLE-BASED: Professional titles (e.g., technician, dealer, consultant, specialist)
  3. BUSINESS-TYPE: Types of businesses (e.g., shop, store, clinic, agency, company, center, studio)
  4. SERVICE-BASED: Services offered (e.g., repair, sales, rental, installation, maintenance)
  5. PRODUCT-BASED: Related products/subcategories
  6. INDUSTRY SYNONYMS: Alternative terms people use for the same thing
  7. NICHE VARIANTS: Specific sub-niches within the industry
- Each keyword should find DIFFERENT businesses, not the same ones
- AVOID generic words and unrelated industries
- AVOID duplicates or near-duplicates
- DO NOT add location names to the keywords (location will be appended separately)
- Make keywords specific enough to find real businesses

Example: "laptop" → ["laptop shop", "laptop repair", "laptop dealer", "computer store", "laptop accessories", "laptop service center", "IT equipment supplier", "notebook computer sales", "refurbished laptop store", "laptop rental"]

Example: "dentist" → ["dentist", "dental clinic", "orthodontist", "dental care center", "cosmetic dentist", "dental surgeon", "dental hospital", "teeth whitening clinic", "dental implant center", "pediatric dentist", "dental lab"]

Return ONLY valid JSON:
{{"keywords": ["keyword1", "keyword2", ...], "business_categories": ["broad category"]}}"""

        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                )
            )

            if not response.text:
                return self._fallback_strategy(keyword)

            data = json.loads(response.text)

            # Ensure original keyword is included
            kw_list = data.get("keywords", [keyword])
            if keyword.lower() not in [k.lower() for k in kw_list]:
                kw_list = [keyword] + kw_list

            return GeneratedStrategy(
                keywords=kw_list,
                business_categories=data.get("business_categories", []),
            )

        except Exception as e:
            print(f"[Strategy] Keyword expansion failed: {e}")
            return self._fallback_strategy(keyword)

    async def generate_additional_keywords(
        self,
        original_keyword: str,
        already_tried: list[str],
        location: str | None = None,
        round_num: int = 1,
    ) -> list[str]:
        """Generate NEW keyword variations that haven't been tried yet.
        
        Called when the main search runs dry but target hasn't been reached.
        Returns a list of fresh keywords to search with.
        """
        client = self._get_client()
        if not client:
            return self._fallback_additional(original_keyword, already_tried)

        tried_str = ", ".join(f'"{k}"' for k in already_tried[:20])
        loc_context = f' in "{location}"' if location else ""

        prompt = f"""You are a lead generation expert. I searched for "{original_keyword}"{loc_context} using these keywords but didn't find enough leads:

Already tried: [{tried_str}]

Generate 6-8 COMPLETELY NEW and DIFFERENT keyword variations to find MORE unique businesses. Think creatively:

Round {round_num} strategy:
- Use DIFFERENT angles: supplier vs buyer, wholesale vs retail, online vs offline
- Try RELATED industries that serve similar customers
- Use informal/local terms people actually search for
- Try broader category terms
- Try hyphenated or compound business terms
- Think about what a business OWNER would name their business

CRITICAL: Do NOT repeat or rephrase any already-tried keywords. Every keyword must be genuinely new.
Do NOT add location names to keywords.

Return ONLY valid JSON:
{{"keywords": ["new_keyword1", "new_keyword2", ...]}}"""

        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9,  # Higher temperature for more creative variations
                )
            )

            if not response.text:
                return self._fallback_additional(original_keyword, already_tried)

            data = json.loads(response.text)
            new_keywords = data.get("keywords", [])

            # Filter out anything already tried
            tried_lower = {k.lower() for k in already_tried}
            new_keywords = [k for k in new_keywords if k.lower() not in tried_lower]

            print(f"[Strategy] Round {round_num} additional keywords: {new_keywords}")
            return new_keywords

        except Exception as e:
            print(f"[Strategy] Additional keyword generation failed: {e}")
            return self._fallback_additional(original_keyword, already_tried)

    def _fallback_strategy(self, keyword: str) -> GeneratedStrategy:
        """Enhanced fallback strategy when AI is unavailable."""
        base = keyword.strip()
        suffixes = [
            "", " shop", " store", " dealer", " service", " repair",
            " supplier", " company", " center", " agency"
        ]
        keywords = []
        for suffix in suffixes:
            kw = f"{base}{suffix}".strip()
            if kw:
                keywords.append(kw)
        return GeneratedStrategy(
            keywords=keywords,
            business_categories=[],
        )

    def _fallback_additional(self, keyword: str, already_tried: list[str]) -> list[str]:
        """Fallback for additional keywords when AI is unavailable."""
        base = keyword.strip()
        tried_lower = {k.lower() for k in already_tried}
        extra_suffixes = [
            " wholesale", " retail", " distributor", " manufacturer",
            " consultant", " specialist", " professional", " outlet",
            " hub", " mart", " depot", " works", " solutions", " enterprise"
        ]
        new_keywords = []
        for suffix in extra_suffixes:
            kw = f"{base}{suffix}".strip()
            if kw.lower() not in tried_lower:
                new_keywords.append(kw)
        return new_keywords[:6]
