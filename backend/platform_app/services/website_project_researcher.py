from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag


PROJECT_PATH_TERMS = (
    "project",
    "projects",
    "property",
    "properties",
    "residential",
    "commercial",
    "ongoing",
    "upcoming",
    "launch",
    "development",
    "developments",
)


RERA_PATTERN = re.compile(
    r"\bP\d{8,15}\b",
    re.IGNORECASE,
)


ACTIVITY_SIGNALS = {
    "new_launch": (
        "new launch",
        "newly launched",
        "launching soon",
        "launch soon",
        "just launched",
        "recent launch",
    ),
    "upcoming": (
        "upcoming project",
        "upcoming projects",
        "coming soon",
        "pre launch",
        "pre-launch",
        "launching soon",
    ),
    "construction_started": (
        "construction started",
        "construction has started",
        "work has started",
        "construction commenced",
        "work commenced",
        "ground breaking",
        "groundbreaking",
    ),
    "active_construction": (
        "under construction",
        "construction in progress",
        "construction ongoing",
        "work in progress",
        "construction progressing",
        "currently under construction",
        "ongoing construction",
    ),
    "booking_started": (
        "booking open",
        "bookings open",
        "booking now open",
        "book now",
        "bookings now open",
        "register your interest",
        "enquire now",
        "sales office",
    ),
    "sales_activity": (
        "available units",
        "available apartments",
        "available flats",
        "units available",
        "apartments available",
        "flats available",
        "for sale",
        "configuration",
        "2 bhk",
        "3 bhk",
        "4 bhk",
    ),
}


COMPLETED_TERMS = (
    "completed project",
    "project completed",
    "construction completed",
    "fully completed",
    "ready to move",
    "ready-to-move",
    "ready possession",
    "ready possession project",
    "possession completed",
    "handed over",
    "handover completed",
    "sold out",
    "sold-out",
)


@dataclass
class WebsiteProject:
    name: str
    url: str
    location: str | None = None
    description: str | None = None
    status: str = "unknown"

    signals: list[str] = field(
        default_factory=list
    )

    evidence: list[str] = field(
        default_factory=list
    )

    maharera_registration_number: str | None = None

    maharera_registration_numbers: list[str] = field(
        default_factory=list
    )


@dataclass
class WebsiteResearch:
    verified: bool = False

    canonical_url: str | None = None

    company_identity_evidence: list[str] = field(
        default_factory=list
    )

    projects: list[WebsiteProject] = field(
        default_factory=list
    )


class WebsiteProjectResearcher:
    """
    Researches the builder's own website.

    This service is responsible for:

    - company identity confirmation
    - active/upcoming project discovery
    - project lifecycle classification
    - MahaRERA registration number extraction

    Completed/sold-out projects are excluded.

    MahaRERA verification itself is intentionally NOT performed
    here. The registration number is passed to the MahaRERA
    verifier by LeadCaptureService.
    """

    def __init__(
        self,
        timeout: float = 12.0,
        max_pages: int = 8,
    ):
        self.timeout = timeout
        self.max_pages = max_pages

    async def research(
        self,
        website: str | None,
        business_name: str,
    ) -> WebsiteResearch:

        if not website:
            return WebsiteResearch()

        website = website.strip()

        if not website:
            return WebsiteResearch()

        if not website.startswith(
            ("http://", "https://")
        ):
            website = "https://" + website

        try:
            root = self._canonical_url(
                website
            )
        except Exception:
            return WebsiteResearch()

        visited: set[str] = set()

        queue: list[str] = [root]

        pages: list[
            tuple[str, str]
        ] = []

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
            },
        ) as client:

            while (
                queue
                and len(pages) < self.max_pages
            ):
                url = queue.pop(0)

                url = self._canonical_url(
                    url
                )

                if url in visited:
                    continue

                visited.add(url)

                try:
                    response = await client.get(
                        url
                    )

                    if response.status_code >= 400:
                        continue

                    content_type = (
                        response.headers.get(
                            "content-type",
                            "",
                        ).lower()
                    )

                    if "text/html" not in content_type:
                        continue

                except Exception as exc:
                    print(
                        "[WebsiteResearch] "
                        f"Failed {url}: {exc}"
                    )
                    continue

                final_url = self._canonical_url(
                    str(response.url)
                )

                pages.append(
                    (
                        final_url,
                        response.text,
                    )
                )

                for link in self._extract_links(
                    response.text,
                    final_url,
                ):
                    if link in visited:
                        continue

                    if not self._same_domain(
                        root,
                        link,
                    ):
                        continue

                    if self._is_project_candidate(
                        link
                    ):
                        queue.append(link)

        return self._build_research(
            root=root,
            business_name=business_name,
            pages=pages,
        )

    def _build_research(
        self,
        root: str,
        business_name: str,
        pages: list[
            tuple[str, str]
        ],
    ) -> WebsiteResearch:

        projects: list[
            WebsiteProject
        ] = []

        identity_evidence: list[str] = []

        for url, html in pages:

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            text = self._clean(
                soup.get_text(
                    " ",
                    strip=True,
                )
            )

            if self._company_matches(
                business_name,
                text,
            ):
                identity_evidence.append(
                    f"Company identity found on {url}"
                )

            signals = self._detect_signals(
                text
            )

            registrations = (
                self._extract_maharera_numbers(
                    text
                )
            )

            completed = (
                self._looks_completed(
                    text
                )
            )

            active = (
                self._classify_status(
                    signals
                )
            )

            # -----------------------------------------------------
            # Completed/sold-out pages are deliberately ignored.
            # -----------------------------------------------------

            if completed:
                continue

            # -----------------------------------------------------
            # A page must provide a meaningful active/upcoming
            # project signal or be a project candidate page.
            # -----------------------------------------------------

            if (
                not active
                and not self._is_project_candidate(
                    url
                )
            ):
                continue

            # A generic /projects page with no project activity
            # is not itself a project record.
            if (
                active == "unknown"
                and not registrations
                and not self._looks_like_project_page(
                    soup,
                    url,
                )
            ):
                continue

            title = self._page_title(
                soup
            )

            project_name = (
                self._extract_project_name(
                    soup,
                    url,
                    business_name,
                )
            )

            if not project_name:
                continue

            location = (
                self._extract_location(
                    text
                )
            )

            evidence = [
                item
                for item in (
                    self._signal_evidence(
                        text,
                        signal,
                    )
                    for signal in signals
                )
                if item
            ]

            if registrations:
                evidence.append(
                    "MahaRERA registration "
                    "number(s) found on builder website: "
                    + ", ".join(registrations)
                )

            projects.append(
                WebsiteProject(
                    name=project_name,
                    url=url,
                    location=location,
                    description=self._description(
                        soup
                    ),
                    status=active,
                    signals=signals,
                    evidence=evidence,
                    maharera_registration_number=(
                        registrations[0]
                        if registrations
                        else None
                    ),
                    maharera_registration_numbers=(
                        registrations
                    ),
                )
            )

        return WebsiteResearch(
            verified=bool(
                identity_evidence
            ),
            canonical_url=root,
            company_identity_evidence=self._unique(
                identity_evidence
            ),
            projects=self._deduplicate_projects(
                projects
            ),
        )

    # =============================================================
    # PROJECT CLASSIFICATION
    # =============================================================

    @staticmethod
    def _classify_status(
        signals: list[str],
    ) -> str:

        if "new_launch" in signals:
            return "new_launch"

        if "upcoming" in signals:
            return "upcoming"

        if (
            "active_construction"
            in signals
            or "construction_started"
            in signals
        ):
            return "ongoing"

        if (
            "booking_started" in signals
            or "sales_activity" in signals
        ):
            return "ongoing"

        return "unknown"

    @staticmethod
    def _looks_completed(
        text: str,
    ) -> bool:

        lowered = text.casefold()

        # We only treat strong lifecycle language as completed.
        # Generic words such as "completed amenities" are ignored.
        return any(
            term in lowered
            for term in COMPLETED_TERMS
        )

    @staticmethod
    def _looks_like_project_page(
        soup: BeautifulSoup,
        url: str,
    ) -> bool:

        if WebsiteProjectResearcher._is_project_candidate(
            url
        ):
            return True

        heading = soup.find(
            ["h1", "h2", "h3"]
        )

        if isinstance(heading, Tag):
            heading_text = heading.get_text(
                " ",
                strip=True,
            ).casefold()

            return any(
                term in heading_text
                for term in (
                    "project",
                    "residences",
                    "residential",
                    "commercial",
                    "tower",
                    "apartments",
                    "homes",
                )
            )

        return False

    # =============================================================
    # MAHARERA EXTRACTION
    # =============================================================

    @staticmethod
    def _extract_maharera_numbers(
        text: str,
    ) -> list[str]:

        matches = RERA_PATTERN.findall(
            text
        )

        result: list[str] = []

        for value in matches:
            value = value.upper()

            if value not in result:
                result.append(value)

        return result

    # =============================================================
    # SIGNALS
    # =============================================================

    @staticmethod
    def _detect_signals(
        text: str,
    ) -> list[str]:

        lowered = text.casefold()

        signals: list[str] = []

        for signal, terms in (
            ACTIVITY_SIGNALS.items()
        ):
            if any(
                term in lowered
                for term in terms
            ):
                signals.append(signal)

        return signals

    @staticmethod
    def _signal_evidence(
        text: str,
        signal: str,
    ) -> str | None:

        lowered = text.casefold()

        for term in ACTIVITY_SIGNALS.get(
            signal,
            (),
        ):
            index = lowered.find(term)

            if index < 0:
                continue

            start = max(
                0,
                index - 120,
            )

            end = min(
                len(text),
                index + len(term) + 180,
            )

            return (
                f"{signal}: "
                f"{text[start:end].strip()}"
            )

        return None

    # =============================================================
    # COMPANY IDENTITY
    # =============================================================

    @staticmethod
    def _company_matches(
        business_name: str,
        text: str,
    ) -> bool:

        business = (
            WebsiteProjectResearcher
            ._normalize(business_name)
        )

        page = (
            WebsiteProjectResearcher
            ._normalize(text)
        )

        if not business:
            return False

        if business in page:
            return True

        business_tokens = {
            token
            for token in business.split()
            if len(token) > 2
        }

        page_tokens = set(
            page.split()
        )

        if not business_tokens:
            return False

        overlap = (
            len(
                business_tokens
                & page_tokens
            )
            / len(business_tokens)
        )

        return overlap >= 0.60

    # =============================================================
    # PROJECT NAME
    # =============================================================

    @staticmethod
    def _extract_project_name(
        soup: BeautifulSoup,
        url: str,
        business_name: str,
    ) -> str | None:

        heading = soup.find(
            "h1"
        )

        if isinstance(heading, Tag):
            value = heading.get_text(
                " ",
                strip=True,
            )

            if value:
                return value

        title = soup.find(
            "title"
        )

        if isinstance(title, Tag):
            value = title.get_text(
                " ",
                strip=True,
            )

            if value:
                value = re.split(
                    r"\s+[|–—-]\s+",
                    value,
                    maxsplit=1,
                )[0].strip()

                if value:
                    return value

        return WebsiteProjectResearcher._project_name_from_url(
            url
        )

    # =============================================================
    # HTML HELPERS
    # =============================================================

    @staticmethod
    def _extract_links(
        html: str,
        base_url: str,
    ) -> list[str]:

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        result: list[str] = []

        for element in soup.find_all(
            "a"
        ):
            if not isinstance(
                element,
                Tag,
            ):
                continue

            href_value: Any = (
                element.attrs.get(
                    "href"
                )
            )

            if href_value is None:
                continue

            if isinstance(
                href_value,
                list,
            ):
                if not href_value:
                    continue

                href = str(
                    href_value[0]
                )
            else:
                href = str(
                    href_value
                )

            if not href:
                continue

            url = urljoin(
                base_url,
                href,
            )

            try:
                url = (
                    WebsiteProjectResearcher
                    ._canonical_url(url)
                )
            except Exception:
                continue

            if url not in result:
                result.append(url)

        return result

    @staticmethod
    def _is_project_candidate(
        url: str,
    ) -> bool:

        path = (
            urlparse(url)
            .path
            .casefold()
        )

        return any(
            term in path
            for term in PROJECT_PATH_TERMS
        )

    @staticmethod
    def _same_domain(
        first: str,
        second: str,
    ) -> bool:

        first_domain = (
            urlparse(first)
            .netloc
            .casefold()
            .removeprefix("www.")
        )

        second_domain = (
            urlparse(second)
            .netloc
            .casefold()
            .removeprefix("www.")
        )

        return first_domain == second_domain

    @staticmethod
    def _page_title(
        soup: BeautifulSoup,
    ) -> str | None:

        title = soup.find(
            "title"
        )

        if isinstance(title, Tag):
            value = title.get_text(
                " ",
                strip=True,
            )

            if value:
                return value

        heading = soup.find(
            ["h1", "h2"]
        )

        if isinstance(heading, Tag):
            value = heading.get_text(
                " ",
                strip=True,
            )

            if value:
                return value

        return None

    @staticmethod
    def _description(
        soup: BeautifulSoup,
    ) -> str | None:

        meta = soup.find(
            "meta",
            attrs={
                "name": re.compile(
                    "^description$",
                    re.I,
                )
            },
        )

        if not isinstance(
            meta,
            Tag,
        ):
            return None

        content = meta.attrs.get(
            "content"
        )

        if isinstance(
            content,
            str,
        ):
            return (
                content.strip()
                or None
            )

        return None

    @staticmethod
    def _extract_location(
        text: str,
    ) -> str | None:

        pattern = (
            r"\b("
            r"Mumbai|Pune|Thane|Navi Mumbai|"
            r"Nashik|Nagpur|Palghar|Raigad|"
            r"Aurangabad|Maharashtra"
            r")\b"
        )

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not matches:
            return None

        return ", ".join(
            WebsiteProjectResearcher._unique(
                matches
            )[:3]
        )

    @staticmethod
    def _project_name_from_url(
        url: str,
    ) -> str:

        path = (
            urlparse(url)
            .path
            .strip("/")
        )

        if not path:
            return "Project"

        value = path.split(
            "/"
        )[-1]

        value = re.sub(
            r"[-_]+",
            " ",
            value,
        )

        return value.title()

    @staticmethod
    def _canonical_url(
        url: str,
    ) -> str:

        parsed = urlparse(url)

        path = parsed.path.rstrip(
            "/"
        )

        return (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{path}"
        )

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
        value: str,
    ) -> str:

        return re.sub(
            r"\s+",
            " ",
            value or "",
        ).strip()

    @staticmethod
    def _unique(
        values: list[str],
    ) -> list[str]:

        result: list[str] = []

        seen: set[str] = set()

        for value in values:
            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)
            result.append(value)

        return result

    @staticmethod
    def _deduplicate_projects(
        projects: list[WebsiteProject],
    ) -> list[WebsiteProject]:

        # First dedupe by URL.
        by_url: dict[
            str,
            WebsiteProject,
        ] = {}

        for project in projects:
            key = project.url.casefold()

            if key not in by_url:
                by_url[key] = project
                continue

            existing = by_url[key]

            existing.signals = (
                WebsiteProjectResearcher._unique(
                    existing.signals
                    + project.signals
                )
            )

            existing.evidence = (
                WebsiteProjectResearcher._unique(
                    existing.evidence
                    + project.evidence
                )
            )

            if (
                not existing.maharera_registration_number
                and project.maharera_registration_number
            ):
                existing.maharera_registration_number = (
                    project.maharera_registration_number
                )

            existing.maharera_registration_numbers = (
                WebsiteProjectResearcher._unique(
                    existing.maharera_registration_numbers
                    + project.maharera_registration_numbers
                )
            )

        # Then collapse obvious duplicate project names
        # discovered on different URLs.
        by_name: dict[
            str,
            WebsiteProject,
        ] = {}

        for project in by_url.values():

            key = (
                WebsiteProjectResearcher
                ._normalize(project.name)
            )

            if not key:
                continue

            if key not in by_name:
                by_name[key] = project
                continue

            existing = by_name[key]

            existing.signals = (
                WebsiteProjectResearcher._unique(
                    existing.signals
                    + project.signals
                )
            )

            existing.evidence = (
                WebsiteProjectResearcher._unique(
                    existing.evidence
                    + project.evidence
                )
            )

            existing.maharera_registration_numbers = (
                WebsiteProjectResearcher._unique(
                    existing.maharera_registration_numbers
                    + project.maharera_registration_numbers
                )
            )

            if (
                not existing.maharera_registration_number
                and project.maharera_registration_number
            ):
                existing.maharera_registration_number = (
                    project.maharera_registration_number
                )

            if (
                existing.status == "unknown"
                and project.status != "unknown"
            ):
                existing.status = project.status

        return list(
            by_name.values()
        )