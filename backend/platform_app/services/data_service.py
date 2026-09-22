from __future__ import annotations

from typing import Any

import httpx


class DataServiceError(RuntimeError):
    pass


class DataServiceClient:

    def __init__(
        self,
        base_url: str,
        timeout: float = 20.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:

        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(
            timeout=self.timeout
        ) as client:

            response = await client.request(
                method,
                url,
                **kwargs,
            )

        if response.status_code >= 400:
            raise DataServiceError(
                f"Data Service request failed: "
                f"{method} {path} "
                f"[{response.status_code}] "
                f"{response.text}"
            )

        try:
            return response.json()
        except Exception as exc:
            raise DataServiceError(
                f"Data Service returned invalid JSON "
                f"for {method} {path}"
            ) from exc

    async def get_known_builders(
        self,
        workspace_id: str,
    ) -> list[dict[str, Any]]:

        response = await self._request(
            "GET",
            "/api/v1/leads/known-builders",
            params={
                "workspace_id": workspace_id,
            },
        )

        return response.get("companies", [])

    async def create_batch(
        self,
        *,
        workspace_id: str,
        location: str,
        target_limit: int,
        keywords: list[str],
    ) -> dict[str, Any]:

        return await self._request(
            "POST",
            "/api/v1/lead-discovery/batches",
            json={
                "workspace_id": workspace_id,
                "location": location,
                "target_limit": target_limit,
                "keywords": keywords,
            },
        )

    async def create_lead(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        return await self._request(
            "POST",
            "/api/v1/leads",
            json=payload,
        )

    async def add_batch_result(
        self,
        *,
        batch_id: str,
        lead_id: str,
        matched_keyword: str | None,
        provider: str | None,
        provider_identifier: str | None,
    ) -> dict[str, Any]:

        return await self._request(
            "POST",
            f"/api/v1/lead-discovery/"
            f"batches/{batch_id}/results",
            json={
                "lead_id": lead_id,
                "matched_keyword": matched_keyword,
                "provider": provider,
                "provider_identifier": provider_identifier,
            },
        )

    async def update_batch(
        self,
        *,
        batch_id: str,
        status: str | None = None,
        raw_results_count: int | None = None,
        final_count: int | None = None,
        duplicate_count: int | None = None,
        rejected_count: int | None = None,
        completed: bool = False,
    ) -> dict[str, Any]:

        return await self._request(
            "PATCH",
            f"/api/v1/lead-discovery/"
            f"batches/{batch_id}",
            json={
                "status": status,
                "raw_results_count": raw_results_count,
                "final_count": final_count,
                "duplicate_count": duplicate_count,
                "rejected_count": rejected_count,
                "completed": completed,
            },
        )