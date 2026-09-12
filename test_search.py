import asyncio
from dotenv import load_dotenv
import os
import json

load_dotenv()

async def test():
    try:
        import httpx
        api_key = os.environ.get('SERPER_API_KEY')
        if api_key:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": "software company in virar", "num": 10}
                )
                data = res.json()
                print("Serper found organic:", len(data.get("organic", [])))
    except Exception as e:
        print("Serper Exception:", e)

if __name__ == "__main__":
    asyncio.run(test())
