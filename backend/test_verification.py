import sys
import asyncio

sys.path.insert(0, "backend")

from platform_app.services.maharera_verifier import MahaRERAVerifier
from platform_app.services.website_project_researcher import WebsiteProjectResearcher


async def main():
    print("=" * 60)
    print("MAHARERA TEST")
    print("=" * 60)

    verifier = MahaRERAVerifier(timeout=15)

    result = await verifier.verify(
        business_name="Omkar Realtors & Developers",
        location="Mumbai",
    )

    print("Verified:", result.verified)
    print("Match score:", result.match_score)
    print("Match type:", result.match_type)
    print("Promoter:", result.promoter_name)
    print("Projects:", len(result.projects))
    print("Source:", result.source_url)

    for project in result.projects[:5]:
        print(
            " -",
            project.registration_number,
            "|",
            project.project_name,
            "|",
            project.promoter_name,
        )

    print()
    print("=" * 60)
    print("BUILDER WEBSITE TEST")
    print("=" * 60)

    researcher = WebsiteProjectResearcher(
        timeout=15,
        max_pages=5,
    )

    website = await researcher.research(
        website="https://www.omkar.com/",
        business_name="Omkar Realtors & Developers",
    )

    print("Verified:", website.verified)
    print("Canonical URL:", website.canonical_url)
    print(
        "Identity evidence:",
        len(website.company_identity_evidence),
    )
    print("Projects/pages:", len(website.projects))

    for project in website.projects[:10]:
        print(
            " -",
            project.name,
            "| signals:",
            project.signals,
        )


if __name__ == "__main__":
    asyncio.run(main())
