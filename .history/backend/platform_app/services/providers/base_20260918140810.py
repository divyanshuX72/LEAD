from typing import Protocol

from pydantic import BaseModel


class RawSearchResult(BaseModel):
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    domain: str | None = None

    phone: str | None = None
    address: str | None = None

    rating: float | None = None
    review_count: int | None = None

    place_id: str | None = None


class SearchProvider(Protocol):

    name: str

    async def is_available(self) -> bool:
        ...

    async def search(
        self,
        query: str,
        location: str | None = None,
        limit: int = 10,
        page: int = 1,
        page_token: str | None = None,
    ) -> tuple[
        list[RawSearchResult],
        str | None,
    ]:
        ...