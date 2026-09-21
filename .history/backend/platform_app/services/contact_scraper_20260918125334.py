import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Set, Any, Optional
from urllib.parse import urljoin, urlparse

class ContactScraper:
    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}', re.IGNORECASE)
    PHONE_REGEX = re.compile(r'(\+91[\s-]?)?[6-9]\d{9}')

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def extract_contacts(self, lead: Dict[str, Any]) -> Dict[str, Optional[List[str]]]:
        """
        Extracts MAXIMUM possible phone numbers and emails from a business lead.
        """
        results = {
            "emails": set(),
            "phone_numbers": set()
        }

        # Step 1: Input
        base_url = lead.get("website") or lead.get("source_url") or ""
        snippet = lead.get("snippet", "")

        if base_url and base_url.startswith('http'):
            parsed = urlparse(base_url)
            domain = parsed.netloc.lower()

            # Skip known low-quality / irrelevant domains
            if not any(skip in domain for skip in ['olx.', 'justdial.com', 'indiamart.com', 'yellowpages.', '.pdf']):
                # Step 2: Scrape important pages (and main page)
                paths_to_try = ['', '/contact', '/contact-us', '/about', '/about-us']
                visited = set()

                async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, verify=False, follow_redirects=True) as client:
                    for path in paths_to_try:
                        target_url = urljoin(base_url, path)
                        if target_url in visited:
                            continue
                        
                        visited.add(target_url)

                        try:
                            resp = await client.get(target_url)
                            if resp.status_code == 200 and 'text/html' in resp.headers.get('Content-Type', '').lower():
                                self._parse_page(resp.text, results)
                        except Exception:
                            # Ignore connection errors, timeouts, etc.
                            pass

        # Step 6: Fallback (VERY IMPORTANT)
        # If website has NO data, use search snippet text
        if not results["emails"] and not results["phone_numbers"] and snippet:
            self._extract_from_text(snippet, results)

        # Step 7: Final Rule
        # IF still nothing found: phone = null, email = null
        emails_list = list(results["emails"])
        phones_list = list(results["phone_numbers"])
        
        return {
            "phone_numbers": phones_list if phones_list else None,
            "emails": emails_list if emails_list else None
        }

    def _parse_page(self, html: str, results: Dict[str, Any]):
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        # Step 3: Search inside HTML text
        text = soup.get_text(separator=' ')
        self._extract_from_text(text, results)

        # Also search tel: and mailto: links
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            if href.lower().startswith('mailto:'):
                email = href[7:].split('?')[0].strip()
                if self.EMAIL_REGEX.match(email):
                    results["emails"].add(email.lower())
            elif href.lower().startswith('tel:'):
                phone = href[4:].strip()
                self._add_phone(phone, results["phone_numbers"])

    def _extract_from_text(self, text: str, results: Dict[str, Any]):
        emails = self.EMAIL_REGEX.findall(text)
        for e in emails:
            e_lower = e.lower()
            if not e_lower.endswith('.png') and not e_lower.endswith('.jpg'):
                results["emails"].add(e_lower)

        phones = self.PHONE_REGEX.finditer(text)
        for match in phones:
            p = match.group(0)
            self._add_phone(p, results["phone_numbers"])

    def _add_phone(self, phone: str, phone_set: Set[str]):
        # Step 4: Clean & Filter
        p_clean = re.sub(r'[^\d+]', '', phone)
        
        # fake numbers
        if "1234567890" in p_clean or "0123456789" in p_clean:
            return
            
        digits_only = re.sub(r'\D', '', p_clean)
        
        # short numbers
        if 10 <= len(digits_only) <= 15:
            # duplicates are handled by set
            # Avoid sequential/repeating garbage like "0000000000"
            if len(set(digits_only)) > 2:
                phone_set.add(phone.strip())
