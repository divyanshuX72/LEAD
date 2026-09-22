from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from typing import Any

import httpx
from bs4 import BeautifulSoup


PROJECT_PATH_TERMS = (
    "project",
    "projects",
    "property",
    "properties",
    "residential",
    "commercial",
    "ongoing",
    "upcoming",
    "new-launch",
    "newlaunch",
    "developments",
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
        "sales",
        "for sale",
        "price",
        "configuration",
        "2 bhk",
        "3 bhk",
        "4 bhk",
    ),
}


@dataclass
class WebsiteProject:
    name: str
    url: str
    location: str | None = None
    description: str | None = None
    signals: list[str] = field(
        default_factory=list
    )
    evidence: list[str] = field(
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

    ContactScraper handles contact extraction.

    This service handles project/activity evidence.
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
            website = (
                "https://" + website
            )

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
                and len(pages)
                < self.max_pages
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
                        )
                        .lower()
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

                discovered_links = (
                    self._extract_links(
                        response.text,
                        final_url,
                    )
                )

                for link in discovered_links:

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
            root,
            business_name,
            pages,
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

            if (
                not signals
                and not self._is_project_candidate(
                    url
                )
            ):
                continue

            title = self._page_title(
                soup
            )

            location = self._extract_location(
                text
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

            projects.append(
                WebsiteProject(
                    name=(
                        title
                        or self._project_name_from_url(
                            url
                        )
                    ),
                    url=url,
                    location=location,
                    description=self._description(
                        soup
                    ),
                    signals=signals,
                    evidence=evidence,
                )
            )

        return WebsiteResearch(
            verified=bool(
                identity_evidence
            ),
            canonical_url=root,
            company_identity_evidence=(
                self._unique(
                    identity_evidence
                )
            ),
            projects=self._deduplicate_projects(
                projects
            ),
        )

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

        terms = ACTIVITY_SIGNALS.get(
            signal,
            (),
        )

        for term in terms:

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

    @staticmethod
def _extract_links(
    html: str,
    base_url: str,
) -> list[str]:

    from bs4.element import Tag

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    result: list[str] = []

    for element in soup.find_all("a"):

        # BeautifulSoup's type stubs can return
        # generic PageElement values here.
        # We only process actual HTML tags.
        if not isinstance(element, Tag):
            continue

        if "href" not in element.attrs:
            continue

        href_value = element.attrs["href"]

        # BeautifulSoup allows href to technically be
        # represented as a string or a list.
        if isinstance(href_value, list):

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

        title = soup.find("title")

        if title is not None:
            title_text = title.get_text(
                " ",
                strip=True,
            )

            if title_text:
                return title_text

        heading = soup.find(
            ["h1", "h2"]
        )

        if heading is not None:
            heading_text = heading.get_text(
                " ",
                strip=True,
            )

            if heading_text:
                return heading_text

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

        if meta is None:
            return None

        attrs: Any = getattr(
            meta,
            "attrs",
            {},
        )

        if not isinstance(
            attrs,
            dict,
        ):
            return None

        content = attrs.get(
            "content"
        )

        if isinstance(
            content,
            str,
        ):
            return content.strip() or None

        if isinstance(
            content,
            list,
        ):
            return " ".join(
                str(item)
                for item in content
            ).strip() or None

        return None

    @staticmethod
    def _extract_location(
        text: str,
    ) -> str | None:

        patterns = (
            r"\b(Mumbai|Pune|Thane|Navi Mumbai|"
            r"Nashik|Nagpur|Palghar|Raigad|"
            r"Aurangabad|Maharashtra)\b"
        )

        matches = re.findall(
            patterns,
            text,
            re.IGNORECASE,
        )

        if not matches:
            return None

        unique = (
            WebsiteProjectResearcher
            ._unique(matches)
        )

        return ", ".join(
            unique[:3]
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
            return "Project page"

        value = path.split("/")[-1]

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

        seen: set[str] = set()
        result: list[WebsiteProject] = []

        for project in projects:

            key = project.url.casefold()

            if key in seen:
                continue

            seen.add(key)
            result.append(project)

        return result