import sys
import asyncio

sys.path.insert(0, "backend")

from platform_app.services.maharera_verifier import MahaRERAVerifier


async def main():
    verifier = MahaRERAVerifier(timeout=15)

    result = await verifier.verify_registration(
        registration_number="P51800017369",
        project_name="Sereno",
        builder_name="Omkar Realtors & Developers",
        location="Andheri",
    )

    print("=" * 60)
    print("MAHARERA REGISTRATION TEST")
    print("=" * 60)
    print("Registration:", "P51800017369")
    print("Verified:", result.verified)
    print("Match type:", result.match_type)
    print("Match score:", result.match_score)
    print("Promoter:", result.promoter_name)
    print("Projects:", len(result.projects))
    print("Source:", result.source_url)
    print()

    for project in result.projects:
        print(
            "PROJECT:",
            project.project_name,
            "| REG:",
            project.registration_number,
            "| PROMOTER:",
            project.promoter_name,
            "| LOCATION:",
            project.location,
            "| DISTRICT:",
            project.district,
        )

    print()
    print("EVIDENCE:")
    for evidence in result.evidence:
        print("-", evidence)


if __name__ == "__main__":
    asyncio.run(main())
