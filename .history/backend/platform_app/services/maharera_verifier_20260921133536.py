from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


MAHARERA_BASE_URL = "https://maharera.maharashtra.gov.in"

PROMOTER_SEARCH_URL = (
    f"{MAHARERA_BASE_URL}/promoters-search-result"
)

PROJECT_SEARCH_URL = (
    f"{MAHARERA_BASE_URL}/projects-search-result"
)

REGISTRATION_PATTERN = re.compile(
    r"\bP\d{8,15}\b",
    re.IGNORECASE,
)

PINCODE_PATTERN = re.compile(
    r"\b\d{6}\b"
)

DATE_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
)


@dataclass
class MahaRERAProject:
    registration_number: str | None = None
    project_name: str | None = None
    promoter_name: str | None = None
    location: str | None = None
    pincode: str | None = None
    district: str | None = None
    last_modified: str | None = None
    details_url: str | None = None
    source_url: str | None = None


@dataclass
class MahaRERAVerification:
    verified: bool = False
    match_type: str = "not_verified"
    match_score: float = 0.0
    promoter_name: str | None = None
    projects: list[MahaRERAProject] = field(
        default_factory=list
    )
    source_url: str | None = None
    evidence: list[str] = field(
        default_factory=list
    )


class MahaRERAVerifier:
    """
    Verifies a discovered builder against the
    official MahaRERA public search.

    Important:
    - This service does not reject leads.
    - Failure to find a MahaRERA match is evidence,
      not a reason to delete the lead.
    """

    def __init__(
        self,
        timeout: float = 15.0,
    ):
        self.timeout = timeout

    async def verify(
        self,
        business_name: str,
        location: str | None = None,
    ) -> MahaRERAVerification:

        business_name = self._clean(
            business_name
        )

        if not business_name:
            return MahaRERAVerification()

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
            },
        ) as client:

            result = await self._search_promoter(
                client,
                business_name,
                location,
            )

            if result.verified:
                return result

            # Fallback: project search.
            return await self._search_projects(
                client,
                business_name,
                location,
            )

    async def _search_promoter(
        self,
        client: httpx.AsyncClient,
        business_name: str,
        location: str | None,
    ) -> MahaRERAVerification:

        params = {
            "promoter_name": business_name,
            "promoter_location": (
                location or ""
            ),
        }

        try:
            response = await client.get(
                PROMOTER_SEARCH_URL,
                params=params,
            )

            response.raise_for_status()

        except Exception as exc:
            print(
                "[MahaRERA] promoter search failed: "
                f"{exc}"
            )
            return MahaRERAVerification(
                source_url=str(
                    response.url
                )
                if "response" in locals()
                else PROMOTER_SEARCH_URL
            )

        projects = self._parse_results(
            response.text,
            str(response.url),
        )

        return self._match_projects(
            business_name=business_name,
            projects=projects,
            source_url=str(response.url),
            location=location,
        )

    async def _search_projects(
        self,
        client: httpx.AsyncClient,
        business_name: str,
        location: str | None,
    ) -> MahaRERAVerification:

        params = {
            "project_name": business_name,
            "project_location": (
                location or ""
            ),
        }

        try:
            response = await client.get(
                PROJECT_SEARCH_URL,
                params=params,
            )

            response.raise_for_status()

        except Exception as exc:
            print(
                "[MahaRERA] project search failed: "
                f"{exc}"
            )

            return MahaRERAVerification(
                source_url=PROJECT_SEARCH_URL
            )

        projects = self._parse_results(
            response.text,
            str(response.url),
        )

        return self._match_projects(
            business_name=business_name,
            projects=projects,
            source_url=str(response.url),
            location=location,
        )

    def _match_projects(
        self,
        business_name: str,
        projects: list[MahaRERAProject],
        source_url: str,
        location: str | None,
    ) -> MahaRERAVerification:

        if not projects:
            return MahaRERAVerification(
                verified=False,
                match_type="not_found",
                source_url=source_url,
                evidence=[
                    "No matching MahaRERA project "
                    "was found in the public search."
                ],
            )

        best_project: MahaRERAProject | None = None
        best_score = 0.0

        for project in projects:

            promoter_score = self._similarity(
                business_name,
                project.promoter_name or "",
            )

            project_score = self._similarity(
                business_name,
                project.project_name or "",
            )

            location_score = self._location_score(
                location,
                project.location,
                project.district,
            )

            score = max(
                promoter_score,
                project_score * 0.75,
            )

            if location_score > 0:
                score = min(
                    1.0,
                    score + (
                        location_score * 0.10
                    ),
                )

            if score > best_score:
                best_score = score
                best_project = project

        if best_project is None:
            return MahaRERAVerification(
                source_url=source_url
            )

        if best_score >= 0.90:
            match_type = "strong"
            verified = True
        elif best_score >= 0.80:
            match_type = "probable"
            verified = True
        elif best_score >= 0.65:
            match_type = "possible"
            verified = False
        else:
            match_type = "not_verified"
            verified = False

        evidence = []

        if verified:
            evidence.append(
                "Builder matched against "
                "official MahaRERA public records."
            )

        if best_project.promoter_name:
            evidence.append(
                "MahaRERA promoter: "
                f"{best_project.promoter_name}"
            )

        if best_project.project_name:
            evidence.append(
                "MahaRERA project: "
                f"{best_project.project_name}"
            )

        return MahaRERAVerification(
            verified=verified,
            match_type=match_type,
            match_score=round(
                best_score * 100,
                2,
            ),
            promoter_name=(
                best_project.promoter_name
            ),
            projects=projects,
            source_url=source_url,
            evidence=evidence,
        )

    def _parse_results(
        self,
        html: str,
        source_url: str,
    ) -> list[MahaRERAProject]:

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        text = soup.get_text(
            "\n",
            strip=True,
        )

        lines = [
            self._clean(line)
            for line in text.splitlines()
        ]

        lines = [
            line
            for line in lines
            if line
        ]

        registration_positions = []

        for index, line in enumerate(lines):

            match = REGISTRATION_PATTERN.search(
                line
            )

            if match:
                registration_positions.append(
                    (
                        index,
                        match.group(0).upper(),
                    )
                )

        projects: list[
            MahaRERAProject
        ] = []

        for position, registration in (
            registration_positions
        ):

            block = lines[
                position:
                min(
                    position + 25,
                    len(lines),
                )
            ]

            project = (
                self._parse_block(
                    block,
                    registration,
                    source_url,
                )
            )

            if project:
                projects.append(project)

        return self._deduplicate_projects(
            projects
        )

    def _parse_block(
        self,
        block: list[str],
        registration: str,
        source_url: str,
    ) -> MahaRERAProject | None:

        if not block:
            return None

        project_name = None
        promoter_name = None
        location = None
        pincode = None
        district = None
        last_modified = None
        details_url = None

        reg_index = 0

        for index, line in enumerate(block):
            if registration.lower() in line.lower():
                reg_index = index
                break

        following = block[
            reg_index + 1:
        ]

        ignored = {
            "view details",
            "view original application",
            "view qr",
            "find route",
            "state",
            "maharashtra",
            "pincode",
            "district",
            "last modified",
            "extension certificate",
            "application",
        }

        candidates = []

        for line in following:

            normalized = line.casefold()

            if normalized in ignored:
                continue

            if REGISTRATION_PATTERN.search(
                line
            ):
                continue

            if DATE_PATTERN.fullmatch(
                line
            ):
                last_modified = line
                continue

            pin_match = PINCODE_PATTERN.search(
                line
            )

            if pin_match:
                pincode = pin_match.group(0)
                continue

            candidates.append(line)

        if candidates:
            project_name = candidates[0]

        if len(candidates) > 1:
            promoter_name = candidates[1]

        if len(candidates) > 2:
            location = candidates[2]

        # Try to locate district from the original
        # block rather than relying only on position.
        for index, line in enumerate(block):

            if line.casefold() == "district":
                if index + 1 < len(block):
                    district = block[
                        index + 1
                    ]
                break

        # Locate a View Details link in the actual HTML
        # is handled separately by URL extraction.
        details_url = self._find_details_url(
            source_url
        )

        return MahaRERAProject(
            registration_number=registration,
            project_name=project_name,
            promoter_name=promoter_name,
            location=location,
            pincode=pincode,
            district=district,
            last_modified=last_modified,
            details_url=details_url,
            source_url=source_url,
        )

    def _find_details_url(
        self,
        source_url: str,
    ) -> str | None:
        # The parser intentionally keeps this nullable.
        # The search result itself is still valid evidence.
        return None

    @staticmethod
    def _similarity(
        left: str,
        right: str,
    ) -> float:

        left = MahaRERAVerifier._normalize(
            left
        )

        right = MahaRERAVerifier._normalize(
            right
        )

        if not left or not right:
            return 0.0

        if left == right:
            return 1.0

        return SequenceMatcher(
            None,
            left,
            right,
        ).ratio()

    @staticmethod
    def _location_score(
        requested: str | None,
        location: str | None,
        district: str | None,
    ) -> float:

        if not requested:
            return 0.0

        requested = (
            MahaRERAVerifier._normalize(
                requested
            )
        )

        candidates = [
            location,
            district,
        ]

        best = 0.0

        for candidate in candidates:

            if not candidate:
                continue

            candidate = (
                MahaRERAVerifier._normalize(
                    candidate
                )
            )

            if requested in candidate:
                best = max(best, 1.0)
                continue

            best = max(
                best,
                SequenceMatcher(
                    None,
                    requested,
                    candidate,
                ).ratio(),
            )

        return best

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:

        value = value.casefold()

        value = re.sub(
            r"\b(private|pvt|limited|ltd|llp|llc)\b",
            " ",
            value,
        )

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

    @staticmethod
    def _clean(
        value: str | None,
    ) -> str:

        if not value:
            return ""

        return re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

    @staticmethod
    def _deduplicate_projects(
        projects: list[MahaRERAProject],
    ) -> list[MahaRERAProject]:

        seen: set[str] = set()
        result = []

        for project in projects:

            key = (
                project.registration_number
                or project.project_name
                or ""
            ).casefold()

            if not key or key in seen:
                continue

            seen.add(key)
            result.append(project)

        return result