from __future__ import annotations

import re
from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class ContactScraper:
    """
    Bounded website crawler for business contact discovery.

    The crawler is intentionally stateless and returns extracted
    information directly to the discovery engine.
    """

    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9._%+-]+"
        r"@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    )

    PHONE_REGEX = re.compile(
        r"(?:\+?\d{1,3}[\s().-]?)?"
        r"(?:\d[\s().-]?){8,14}\d"
    )

    IMPORTANT_PATH_TERMS = (
        "contact",
        "about",
        "team",
        "leadership",
        "management",
        "sales",
        "business-development",
        "projects",
        "properties",
        "portfolio",
    )

    SKIP_EXTENSIONS = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".zip",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
    )

    def __init__(
        self,
        timeout: float = 8,
        max_pages: int = 8,
    ):
        self.timeout = timeout
        self.max_pages = max_pages

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }

    async def extract_contacts(
        self,
        lead: dict[str, Any],
    ) -> dict[str, Any]:

        result = {
            "emails": set(),
            "phone_numbers": set(),
            "linkedin_url": None,
            "instagram_url": None,
            "facebook_url": None,
            "contact_name": None,
            "designation": None,
            "pages_visited": [],
        }

        base_url = (
            lead.get("website")
            or lead.get("source_url")
            or ""
        )

        if not base_url.startswith("http"):
            self._extract_from_text(
                lead.get("snippet", ""),
                result,
            )
            return self._finalize(result)

        parsed = urlparse(base_url)

        if not parsed.netloc:
            return self._finalize(result)

        hostname = parsed.netloc.lower()

        if any(
            blocked in hostname
            for blocked in (
                "olx.",
                "justdial.",
                "indiamart.",
                "yellowpages.",
                "facebook.com",
                "instagram.com",
                "linkedin.com",
            )
        ):
            self._extract_from_text(
                lead.get("snippet", ""),
                result,
            )
            return self._finalize(result)

        origin = (
            f"{parsed.scheme}://{parsed.netloc}"
        )

        queue: deque[str] = deque(
            [
                base_url,
                urljoin(origin, "/contact"),
                urljoin(origin, "/contact-us"),
                urljoin(origin, "/about"),
                urljoin(origin, "/about-us"),
                urljoin(origin, "/team"),
                urljoin(origin, "/leadership"),
                urljoin(origin, "/projects"),
            ]
        )

        queued = set(queue)
        visited: set[str] = set()

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True,
            verify=False,
        ) as client:

            while queue and len(visited) < self.max_pages:

                url = queue.popleft()

                normalized_url = self._normalize_url(
                    url
                )

                if (
                    not normalized_url
                    or normalized_url in visited
                ):
                    continue

                if not self._same_domain(
                    normalized_url,
                    hostname,
                ):
                    continue

                if self._is_ignored_url(normalized_url):
                    continue

                visited.add(normalized_url)

                try:
                    response = await client.get(
                        normalized_url
                    )
                except Exception:
                    continue

                result["pages_visited"].append(
                    normalized_url
                )

                content_type = (
                    response.headers.get(
                        "content-type",
                        "",
                    ).lower()
                )

                if (
                    response.status_code != 200
                    or "text/html" not in content_type
                ):
                    continue

                self._parse_page(
                    response.text,
                    result,
                )

                if len(visited) >= self.max_pages:
                    break

                soup = BeautifulSoup(
                    response.text,
                    "html.parser",
                )

                for anchor in soup.find_all(
                    "a",
                    href=True,
                ):
                    href = anchor.get(
                        "href",
                        "",
                    ).strip()

                    if not href:
                        continue

                    candidate = self._normalize_url(
                        urljoin(
                            normalized_url,
                            href,
                        )
                    )

                    if not candidate:
                        continue

                    if not self._same_domain(
                        candidate,
                        hostname,
                    ):
                        continue

                    if self._is_ignored_url(
                        candidate
                    ):
                        continue

                    if candidate in visited:
                        continue

                    path = (
                        urlparse(candidate)
                        .path.lower()
                    )

                    text = (
                        anchor.get_text(
                            " ",
                            strip=True,
                        )
                        .lower()
                    )

                    priority = (
                        any(
                            term in path
                            for term in self.IMPORTANT_PATH_TERMS
                        )
                        or any(
                            term in text
                            for term in self.IMPORTANT_PATH_TERMS
                        )
                    )

                    if priority:
                        queue.appendleft(candidate)
                    else:
                        queue.append(candidate)

        if not result["emails"] and not result["phone_numbers"]:
            self._extract_from_text(
                lead.get("snippet", ""),
                result,
            )

        return self._finalize(result)

    def _parse_page(
        self,
        html: str,
        result: dict[str, Any],
    ) -> None:

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        for element in soup(
            ["script", "style", "noscript"]
        ):
            element.extract()

        text = soup.get_text(
            separator=" ",
            strip=True,
        )

        self._extract_from_text(
            text,
            result,
        )

        for anchor in soup.find_all(
            "a",
            href=True,
        ):
            href = anchor.get(
                "href",
                "",
            ).strip()

            lower = href.lower()

            if lower.startswith("mailto:"):
                email = (
                    href[7:]
                    .split("?")[0]
                    .strip()
                )

                if self.EMAIL_REGEX.fullmatch(
                    email
                ):
                    result["emails"].add(
                        email.lower()
                    )

            elif lower.startswith("tel:"):
                self._add_phone(
                    href[4:],
                    result["phone_numbers"],
                )

            elif "linkedin.com/" in lower:
                if not result["linkedin_url"]:
                    result["linkedin_url"] = href

            elif "instagram.com/" in lower:
                if not result["instagram_url"]:
                    result["instagram_url"] = href

            elif "facebook.com/" in lower:
                if not result["facebook_url"]:
                    result["facebook_url"] = href

    def _extract_from_text(
        self,
        text: str,
        result: dict[str, Any],
    ) -> None:

        if not text:
            return

        for email in self.EMAIL_REGEX.findall(text):
            email = email.lower().strip()

            if not email.endswith(
                (".png", ".jpg", ".jpeg")
            ):
                result["emails"].add(email)

        for match in self.PHONE_REGEX.finditer(text):
            self._add_phone(
                match.group(0),
                result["phone_numbers"],
            )

    def _add_phone(
        self,
        phone: str,
        phone_set: set[str],
    ) -> None:

        digits = re.sub(
            r"\D",
            "",
            phone,
        )

        if len(digits) < 10 or len(digits) > 15:
            return

        if len(set(digits)) <= 2:
            return

        if (
            "1234567890" in digits
            or "0123456789" in digits
        ):
            return

        normalized = f"+{digits}"

        phone_set.add(normalized)

    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str | None:

        try:
            parsed = urlparse(url)

            if parsed.scheme not in (
                "http",
                "https",
            ):
                return None

            if not parsed.netloc:
                return None

            return (
                f"{parsed.scheme}://"
                f"{parsed.netloc}"
                f"{parsed.path.rstrip('/')}"
            )

        except Exception:
            return None

    @staticmethod
    def _same_domain(
        url: str,
        hostname: str,
    ) -> bool:

        current = urlparse(url).netloc.lower()

        current = current.removeprefix("www.")
        hostname = hostname.removeprefix("www.")

        return (
            current == hostname
            or current.endswith(
                f".{hostname}"
            )
        )

    def _is_ignored_url(
        self,
        url: str,
    ) -> bool:

        parsed = urlparse(url)

        path = parsed.path.lower()

        if path.endswith(
            self.SKIP_EXTENSIONS
        ):
            return True

        return any(
            blocked in parsed.netloc.lower()
            for blocked in (
                "login.",
                "accounts.",
            )
        )

    @staticmethod
    def _finalize(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        return {
            "emails": sorted(
                result["emails"]
            ),
            "phone_numbers": sorted(
                result["phone_numbers"]
            ),
            "linkedin_url": result[
                "linkedin_url"
            ],
            "instagram_url": result[
                "instagram_url"
            ],
            "facebook_url": result[
                "facebook_url"
            ],
            "contact_name": result[
                "contact_name"
            ],
            "designation": result[
                "designation"
            ],
            "pages_visited": result[
                "pages_visited"
            ],
        }