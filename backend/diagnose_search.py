"""
Lead Discovery Diagnostic Script
Tests each step of the pipeline to find where it breaks.
"""
import asyncio
import sys
import os

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(__file__))

async def run_diagnostics():
    print("=" * 60)
    print("  LEAD DISCOVERY DIAGNOSTIC")
    print("=" * 60)
    
    # ─── Step 1: Check Settings & API Keys ───
    print("\n[1/6] Checking Settings & API Keys...")
    try:
        from platform_app.config.settings import get_settings
        settings = get_settings()
        print(f"  SERPER_API_KEY:      {'✅ SET' if settings.SERPER_API_KEY else '❌ MISSING'}")
        print(f"  TAVILY_API_KEY:      {'✅ SET' if settings.TAVILY_API_KEY else '❌ MISSING'}")
        print(f"  GOOGLE_MAPS_API_KEY: {'✅ SET' if settings.GOOGLE_MAPS_API_KEY else '⚠️ MISSING (optional)'}")
        print(f"  BRAVE_API_KEY:       {'✅ SET' if settings.BRAVE_API_KEY else '⚠️ MISSING (optional)'}")
        print(f"  GEMINI_API_KEY:      {'✅ SET' if settings.GEMINI_API_KEY else '❌ MISSING'}")
        print(f"  GEMINI_MODEL:        {settings.GEMINI_MODEL}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return

    # ─── Step 2: Check Providers ───
    print("\n[2/6] Checking Search Providers...")
    try:
        from platform_app.services.providers.registry import ProviderRegistry
        registry = ProviderRegistry()
        available = await registry.get_available_providers()
        print(f"  Available providers: {len(available)}")
        for p in available:
            print(f"    ✅ {p.name}")
        if not available:
            print("  ❌ NO PROVIDERS AVAILABLE! Search cannot work.")
            print("     At minimum DuckDuckGo should be available (no API key needed)")
            return
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # ─── Step 3: Test DuckDuckGo Search ───
    print("\n[3/6] Testing DuckDuckGo search (no API key needed)...")
    try:
        from platform_app.services.providers.duckduckgo import DuckDuckGoProvider
        ddg = DuckDuckGoProvider()
        results, _ = await ddg.search("B2B software companies", limit=5)
        print(f"  Results: {len(results)}")
        for r in results[:3]:
            print(f"    → {r.title[:50] if r.title else 'No title'} | {r.domain}")
        if not results:
            print("  ⚠️ DuckDuckGo returned 0 results (might be rate-limited or blocked)")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

    # ─── Step 4: Test Serper Search ───
    print("\n[4/6] Testing Serper search...")
    try:
        from platform_app.services.providers.serper import SerperProvider
        serper = SerperProvider()
        if await serper.is_available():
            results, _ = await serper.search("B2B software companies", limit=5)
            print(f"  Results: {len(results)}")
            for r in results[:3]:
                print(f"    → {r.title[:50] if r.title else 'No title'} | {r.domain}")
            if not results:
                print("  ⚠️ Serper returned 0 results — API key might be invalid or expired")
        else:
            print("  ⚠️ Serper not available (no API key)")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

    # ─── Step 5: Test Tavily Search ───
    print("\n[5/6] Testing Tavily search...")
    try:
        from platform_app.services.providers.tavily import TavilyProvider
        tavily = TavilyProvider()
        if await tavily.is_available():
            results, _ = await tavily.search("B2B software companies", limit=5)
            print(f"  Results: {len(results)}")
            for r in results[:3]:
                print(f"    → {r.title[:50] if r.title else 'No title'} | {r.domain}")
            if not results:
                print("  ⚠️ Tavily returned 0 results — API key might be invalid or expired")
        else:
            print("  ⚠️ Tavily not available (no API key)")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

    # ─── Step 6: Test Gemini AI (Search Strategy) ───
    print("\n[6/6] Testing Gemini AI for search strategy...")
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Say 'hello' in one word only.",
        )
        print(f"  Gemini Response: {(response.text or '').strip()}")
        print("  ✅ Gemini AI is working!")
    except Exception as e:
        print(f"  ❌ Gemini FAILED: {e}")
        import traceback
        traceback.print_exc()

    # ─── Step 7: Check Database — Business Profile ───
    print("\n[BONUS] Checking Database for Business Profile...")
    try:
        from platform_app.database.engine import AsyncSessionFactory
        from sqlalchemy import text

        async with AsyncSessionFactory() as db:
            result = await db.execute(text("SELECT id, company_id, summary FROM business_profiles LIMIT 5"))
            rows = result.fetchall()
            if rows:
                print(f"  ✅ Found {len(rows)} business profile(s):")
                for row in rows:
                    summary_preview = (row[2] or "")[:60]
                    print(f"    ID: {row[0][:12]}... | Company: {row[1][:12]}... | Summary: {summary_preview}...")
            else:
                print("  ❌ NO BUSINESS PROFILES FOUND!")
                print("     The orchestrator requires a business profile to generate search strategy.")
                print("     This is likely why discovery shows 0 results.")
                print("     Fix: Go to Settings > Company Profile and fill it out, or create one via API.")
    except Exception as e:
        print(f"  ❌ DB Check FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
