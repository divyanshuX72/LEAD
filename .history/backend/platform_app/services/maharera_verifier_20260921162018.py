from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import httpx
from bs4 import BeautifulSoup


MAHARERA_BASE_URL = (
    "https://maharera.maharashtra.gov.in"
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
    Verifies a project using the MahaRERA registration number
    extracted from the builder's own website.

    Flow:

        Builder website
            ↓
        P-registration number
            ↓
        Official MahaRERA project search
            ↓
        Registration match
            ↓
        Project name + promoter + location verification

    This service does NOT discover builders.
    """

    def __init__(
        self,
        timeout: float = 15.0,
    ):
        self.timeout = timeout

    async def verify_registration(
        self,
        registration_number: str,
        project_name: str | None = None,
        builder_name: str | None = None,
        location: str | None = None,
    ) -> MahaRERAVerification:

        normalized_registration = (
            self._normalize_registration(
                registration_number
            )
        )

        if not normalized_registration:
            return MahaRERAVerification(
                match_type="invalid_registration"
            )

        params = {
            # MahaRERA's official project search
            # accepts Project Name / MahaRERA
            # Registration Number in this field.
            "project_name": normalized_registration,
        }

        source_url = PROJECT_SEARCH_URL

        try:
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

                response = await client.get(
                    PROJECT_SEARCH_URL,
                    params=params,
                )

                response.raise_for_status()

                source_url = str(
                    response.url
                )

                projects = (
                    self._parse_results(
                        response.text,
                        source_url,
                    )
                )

        except Exception as exc:

            print(
                "[MahaRERA] "
                "registration lookup failed "
                f"for {registration_number}: "
                f"{exc}"
            )

            return MahaRERAVerification(
                verified=False,
                match_type="search_failed",
                source_url=source_url,
                evidence=[
                    "MahaRERA registration lookup "
                    "could not be completed."
                ],
            )

        matching = [
            project
            for project in projects
            if (
                project.registration_number
                and
                project.registration_number.casefold()
                == registration_number.casefold()
            )
        ]

        if not matching:

            return MahaRERAVerification(
                verified=False,
                match_type="not_found",
                source_url=source_url,
                evidence=[
                    "Registration number was not found "
                    "in the official MahaRERA project search."
                ],
            )

        best_project = self._choose_best_project(
            matching,
            project_name=project_name,
            builder_name=builder_name,
            location=location,
        )

        project_score = (
            self._project_name_score(
                project_name,
                best_project.project_name,
            )
            if project_name
            else 1.0
        )

        promoter_score = (
            self._similarity(
                builder_name,
                best_project.promoter_name,
            )
            if builder_name
            else 1.0
        )

        location_score = (
            self._location_score(
                location,
                best_project.location,
                best_project.district,
            )
            if location
            else 1.0
        )

        # Registration number itself is the primary identity
        # match. Project/promoter/location provide confirmation.
        match_score = (
            0.50
            + (0.25 * project_score)
            + (0.20 * promoter_score)
            + (0.05 * location_score)
        )

        match_score = min(
            1.0,
            match_score,
        )

        if (
            project_score >= 0.75
            and promoter_score >= 0.65
            and location_score >= 0.40
        ):
            match_type = "strong"
            verified = True

        elif (
            project_score >= 0.60
            and promoter_score >= 0.50
        ):
            match_type = "probable"
            verified = True

        else:
            match_type = "registration_found_identity_uncertain"
            verified = False

        evidence = [
            "MahaRERA registration number matched "
            f"official record: {registration_number}"
        ]

        if best_project.project_name:
            evidence.append(
                "MahaRERA project: "
                f"{best_project.project_name}"
            )

        if best_project.promoter_name:
            evidence.append(
                "MahaRERA promoter: "
                f"{best_project.promoter_name}"
            )

        if best_project.location:
            evidence.append(
                "MahaRERA location: "
                f"{best_project.location}"
            )

        if verified:
            evidence.append(
                "Project identity is consistent with "
                "the builder website information."
            )

        return MahaRERAVerification(
            verified=verified,
            match_type=match_type,
            match_score=round(
                match_score * 100,
                2,
            ),
            promoter_name=(
                best_project.promoter_name
            ),
            projects=matching,
            source_url=source_url,
            evidence=evidence,
        )

    def _choose_best_project(
        self,
        projects: list[MahaRERAProject],
        project_name: str | None,
        builder_name: str | None,
        location: str | None,
    ) -> MahaRERAProject:

        return max(
            projects,
            key=lambda project: (
                self._project_name_score(
                    project_name,
                    project.project_name,
                )
                + self._similarity(
                    builder_name,
                    project.promoter_name,
                )
                + self._location_score(
                    location,
                    project.location,
                    project.district,
                )
            ),
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

        projects: list[
            MahaRERAProject
        ] = []

        for index, line in enumerate(lines):

            match = REGISTRATION_PATTERN.fullmatch(
                line
            )

            if not match:
                continue

            registration = (
                match.group(0).upper()
            )

            block = lines[
                index:
                min(
                    index + 25,
                    len(lines),
                )
            ]

            project = self._parse_block(
                block,
                registration,
                source_url,
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

        following = block[1:]

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
            "certificate",
        }

        candidates: list[str] = []

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
                pincode = (
                    pin_match.group(0)
                )
                continue

            if normalized in {
                "maharashtra",
            }:
                continue

            candidates.append(line)

        if candidates:
            project_name = candidates[0]

        if len(candidates) > 1:
            promoter_name = candidates[1]

        if len(candidates) > 2:
            location = candidates[2]

        for index, line in enumerate(
            block
        ):

            if line.casefold() == "district":

                if index + 1 < len(block):
                    district = block[
                        index + 1
                    ]

                break

        return MahaRERAProject(
            registration_number=registration,
            project_name=project_name,
            promoter_name=promoter_name,
            location=location,
            pincode=pincode,
            district=district,
            last_modified=last_modified,
            details_url=None,
            source_url=source_url,
        )

    @staticmethod
    def _normalize_registration(
        value: str | None,
    ) -> str | None:

        if not value:
            return None

        match = REGISTRATION_PATTERN.search(
            value.upper()
        )

        if not match:
            return None

        return match.group(0).upper()

    @staticmethod
    def _project_name_score(
        requested: str | None,
        actual: str | None,
    ) -> float:

        if not requested or not actual:
            return 0.0

        requested_normalized = (
            MahaRERAVerifier._normalize(
                requested
            )
        )

        actual_normalized = (
            MahaRERAVerifier._normalize(
                actual
            )
        )

        if not requested_normalized:
            return 0.0

        if (
            requested_normalized
            == actual_normalized
        ):
            return 1.0

        if (
            requested_normalized
            in actual_normalized
            or actual_normalized
            in requested_normalized
        ):
            return 0.90

        return SequenceMatcher(
            None,
            requested_normalized,
            actual_normalized,
        ).ratio()

    @staticmethod
    def _similarity(
        left: str | None,
        right: str | None,
    ) -> float:

        if not left or not right:
            return 0.0

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

        left_tokens = set(
            left.split()
        )

        right_tokens = set(
            right.split()
        )

        if left_tokens and right_tokens:
            overlap = (
                len(
                    left_tokens
                    & right_tokens
                )
                / len(left_tokens)
            )

            if overlap >= 0.75:
                return max(
                    overlap,
                    0.85,
                )

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
            return 1.0

        requested = (
            MahaRERAVerifier._normalize(
                requested
            )
        )

        best = 0.0

        for candidate in (
            location,
            district,
        ):

            if not candidate:
                continue

            candidate = (
                MahaRERAVerifier._normalize(
                    candidate
                )
            )

            if requested in candidate:
                best = max(
                    best,
                    1.0,
                )
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

        result: list[
            MahaRERAProject
        ] = []

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