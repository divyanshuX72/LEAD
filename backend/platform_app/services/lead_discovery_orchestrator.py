"""
Lead Discovery Orchestrator — Multi-Tenant with Stop Conditions + Keyword Retry

Multi-keyword search engine with batch management.
Searches until target lead count is reached, timeout, or sources exhausted.
Emits Socket.IO events for real-time progress.

STOP CONDITIONS:
A. TARGET ACHIEVED: results_found >= target → completed / target_achieved
B. HARD TIMEOUT: elapsed > 120s → partial / timeout
C. PROVIDERS EXHAUSTED + RETRIES EXHAUSTED: all done, target not met → partial / providers_exhausted
D. MAX RETRY ROUNDS: retried 3 times with new keywords, still not enough → partial / retries_exhausted

RETRY LOGIC:
When no progress is detected (5 cycles), instead of stopping:
1. Generate additional keywords using AI
2. Queue new keyword × provider combinations
3. Reset no_progress counter
4. Allow up to MAX_RETRY_ROUNDS (3) retries
"""

import asyncio
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.models.lead_batch import LeadBatch, BatchStatus
from platform_app.models.lead_batch_keyword import LeadBatchKeyword
from platform_app.models.lead import Lead
from platform_app.models.lead_source import LeadSource

from platform_app.services.providers.registry import ProviderRegistry
from platform_app.services.search_strategy import SearchStrategyEngine
from platform_app.services.contact_scraper import ContactScraper

try:
    from platform_app.core.events import emit_event
except ImportError:
    emit_event = None

# ── Constants ────────────────────────────────────────────────────────────
MAX_NO_PROGRESS_CYCLES = 5       # More patient before triggering retry
MAX_RETRY_ROUNDS = 3             # How many times to expand keywords before giving up
MAX_PAGES_PER_KEYWORD = 8        # Up from 5 → more pagination
HARD_TIMEOUT_SECONDS = 120       # Up from 45s → more time for retries


class LeadDiscoveryOrchestrator:
    """Orchestrates multi-keyword lead discovery with batch management and keyword retry."""

    def __init__(self, session: AsyncSession, company_id: str | None = None):
        self.session = session
        self.company_id = company_id
        self.db_lock = asyncio.Lock()
        self.provider_registry = ProviderRegistry()
        self.strategy_engine = SearchStrategyEngine()

    async def _emit(self, event: str, data: dict, room: str = "lead_agent"):
        if emit_event:
            try:
                await emit_event(event, data, room=room)
            except Exception:
                pass

    async def run_discovery(
        self,
        batch: LeadBatch,
        keywords: list[str],
        location: str,
        limit: int = 50,
    ) -> str:
        """Run a multi-keyword lead discovery session with keyword retry.
        
        Returns the batch_id.
        """
        batch_id = batch.id
        
        # Batch was loaded in a different session for the request. We must merge it.
        batch = await self.session.merge(batch)
        
        start_time = time.monotonic()
        last_activity_time = start_time

        await self._emit("search_started", {
            "batch_id": batch_id,
            "keywords": keywords,
            "location": location,
            "limit": limit,
        })

        try:
            # 2. Update status
            batch.status = BatchStatus.RUNNING.value
            batch.started_at = datetime.now(timezone.utc)
            await self.session.commit()

            # 3. Get providers
            providers = await self.provider_registry.get_available_providers()
            if not providers:
                raise ValueError("No search providers available. Configure API keys in .env")

            print(f"[Discovery] Providers: {[p.name for p in providers]}")

            # 4. Expand keywords using AI — enhanced to 8-12 per keyword
            all_keywords = []
            for kw in keywords:
                strategy = await self.strategy_engine.generate_strategy(kw, location)
                if strategy and strategy.keywords:
                    all_keywords.extend(strategy.keywords)
                else:
                    all_keywords.append(kw)
            
            # Deduplicate while preserving order
            seen_kw = set()
            all_keywords = [x for x in all_keywords if not (x.lower() in seen_kw or seen_kw.add(x.lower()))]
            print(f"[Discovery] Expanded Keywords ({len(all_keywords)}): {all_keywords}")

            # Track all tried keywords for retry logic
            all_tried_keywords = set(k.lower() for k in all_keywords)

            # 5. Build search queue
            queue = asyncio.Queue()
            for kw in all_keywords:
                for provider in providers:
                    await queue.put((kw, provider, location, 1, None))

            # 6. Shared state
            state = {
                "imported": 0,
                "raw_total": 0,
                "duplicates": 0,
                "rejected": 0,
                "running": 0,
                "no_progress_cycles": 0,
                "last_results_count": 0,
                "retry_round": 0,
            }
            keyword_results: dict[str, int] = {}
            max_reached = asyncio.Event()
            seen_dedupe_keys = set()
            stop_reason: str | None = None
            retry_triggered = asyncio.Event()

            def _check_no_progress() -> bool:
                """Check if results haven't increased for N cycles."""
                if state["imported"] == state["last_results_count"]:
                    state["no_progress_cycles"] += 1
                else:
                    state["no_progress_cycles"] = 0
                state["last_results_count"] = state["imported"]
                return state["no_progress_cycles"] >= MAX_NO_PROGRESS_CYCLES

            # 7. Worker
            async def worker(worker_id: int):
                nonlocal stop_reason
                while not max_reached.is_set():
                    try:
                        task = await asyncio.wait_for(queue.get(), timeout=2.0)
                    except asyncio.TimeoutError:
                        if queue.empty() and state["running"] == 0:
                            break
                        continue
                    except asyncio.CancelledError:
                        break

                    kw, provider, loc, page, page_token = task
                    state["running"] += 1

                    retry_info = f" [Retry {state['retry_round']}]" if state["retry_round"] > 0 else ""
                    await self._emit("search_progress", {
                        "batch_id": batch_id,
                        "status": "running",
                        "current_keyword": kw,
                        "leads_found": state["imported"],
                        "leads_target": limit,
                        "duplicates": state["duplicates"],
                        "scanned": state["raw_total"],
                        "retry_round": state["retry_round"],
                        "message": f"Searching: {kw} in {loc} (via {provider.name}){retry_info}",
                    })

                    try:
                        raw_results, next_token = await provider.search(
                            kw, location=loc, limit=20, page=page, page_token=page_token
                        )
                        state["raw_total"] += len(raw_results)

                        leads_to_process = []
                        for raw in raw_results:
                            leads_to_process.append(self._normalize_result(raw, kw, provider.name, loc))

                        scraper = ContactScraper()
                        scrape_tasks = []
                        for data in leads_to_process:
                            scrape_tasks.append(scraper.extract_contacts(data))
                        
                        scraped_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

                        for lead_data, scraped in zip(leads_to_process, scraped_results):
                            if max_reached.is_set():
                                break

                            if isinstance(scraped, dict):
                                lead_data["emails"] = scraped.get("emails") or []
                                lead_data["phones"] = scraped.get("phone_numbers") or []
                            else:
                                lead_data["emails"] = []
                                lead_data["phones"] = []

                            if lead_data.get("email") and lead_data["email"] not in lead_data["emails"]:
                                lead_data["emails"].append(lead_data["email"])
                            if lead_data.get("phone") and lead_data["phone"] not in lead_data["phones"]:
                                lead_data["phones"].append(lead_data["phone"])

                            if not self._validate_lead(lead_data):
                                state["rejected"] += 1
                                continue

                            dedupe_key = self._compute_dedupe_key(lead_data)
                            if dedupe_key in seen_dedupe_keys:
                                state["duplicates"] += 1
                                async with self.db_lock:
                                    batch.duplicate_count = state["duplicates"]
                                    await self.session.commit()
                                continue

                            # Check DB for duplicate in batch
                            async with self.db_lock:
                                existing = await self._find_duplicate_in_batch(
                                    batch_id, dedupe_key, lead_data
                                )
                                if existing:
                                    state["duplicates"] += 1
                                    seen_dedupe_keys.add(dedupe_key)
                                    batch.duplicate_count = state["duplicates"]
                                    await self.session.commit()
                                    continue

                                # Save lead with company_id
                                lead = Lead(
                                    company_id=self.company_id,
                                    batch_id=batch_id,
                                    business_name=lead_data["business_name"],
                                    emails=lead_data.get("emails", []),
                                    phones=lead_data.get("phones", []),
                                    website=lead_data.get("website"),
                                    linkedin_url=lead_data.get("linkedin_url"),
                                    facebook_url=lead_data.get("facebook_url"),
                                    instagram_url=lead_data.get("instagram_url"),
                                    address=lead_data.get("address"),
                                    city=lead_data.get("city") or loc,
                                    matched_keyword=kw,
                                    source_primary=provider.name,
                                    source_url=lead_data.get("source_url"),
                                    rating=lead_data.get("rating"),
                                    review_count=lead_data.get("review_count"),
                                    dedupe_key=dedupe_key,
                                    quality_status=lead_data.get("quality_status", "valid")
                                )
                                self.session.add(lead)
                                await self.session.flush()

                                # Save source record
                                source = LeadSource(
                                    lead_id=lead.id,
                                    provider=provider.name,
                                    source_url=lead_data.get("source_url"),
                                    matched_keyword=kw,
                                    provider_identifier=lead_data.get("place_id"),
                                )
                                self.session.add(source)
                                
                                # Real-time batch update
                                batch.final_count = state["imported"] + 1
                                batch.raw_results_count = state["raw_total"]
                                batch.duplicate_count = state["duplicates"]
                                batch.rejected_count = state["rejected"]
                                if batch.final_count >= limit:
                                    batch.status = BatchStatus.COMPLETED.value
                                else:
                                    batch.status = BatchStatus.RUNNING.value
                                    
                                await self.session.commit()

                            seen_dedupe_keys.add(dedupe_key)
                            state["imported"] += 1
                            
                            # Update activity time since we found a lead
                            nonlocal last_activity_time
                            last_activity_time = time.monotonic()

                            # Track per-keyword results
                            keyword_results[kw] = keyword_results.get(kw, 0) + 1

                            await self._emit("lead_discovered", {
                                "batch_id": batch_id,
                                "lead_id": lead.id,
                                "name": lead.business_name,
                                "leads_found": state["imported"],
                                "leads_target": limit,
                            })

                            # STOP CONDITION A: Target achieved
                            if state["imported"] >= limit:
                                stop_reason = "target_achieved"
                                max_reached.set()
                                break

                        # After processing a batch of results, check no-progress
                        if not max_reached.is_set():
                            if _check_no_progress():
                                # Instead of stopping, signal retry
                                retry_triggered.set()

                        # Queue next page if needed — increased limit
                        if (not max_reached.is_set()
                                and len(raw_results) > 0
                                and page < MAX_PAGES_PER_KEYWORD):
                            if next_token or provider.name in ["serper", "brave"]:
                                await queue.put((kw, provider, loc, page + 1, next_token))

                    except Exception as e:
                        print(f"[Discovery Worker {worker_id}] Error: {e}")

                    finally:
                        state["running"] -= 1
                        queue.task_done()

            # 8. Start workers
            num_workers = min(5, len(providers) * 2)
            workers = [asyncio.create_task(worker(i)) for i in range(num_workers)]

            # 9. Main loop with retry logic
            while not max_reached.is_set():
                await asyncio.sleep(0.5)
                
                # Check for hard timeout
                elapsed = time.monotonic() - start_time
                if elapsed > HARD_TIMEOUT_SECONDS:
                    stop_reason = "timeout"
                    max_reached.set()
                    break
                
                # Check for manual stop
                async with self.db_lock:
                    await self.session.refresh(batch, ['status'])
                    if batch.status == "stopped":
                        stop_reason = "user_stopped"
                        max_reached.set()
                        break

                # Check if retry was triggered (no progress detected by workers)
                if retry_triggered.is_set():
                    retry_triggered.clear()
                    
                    if state["retry_round"] < MAX_RETRY_ROUNDS:
                        state["retry_round"] += 1
                        state["no_progress_cycles"] = 0
                        
                        print(f"[Discovery] No progress — triggering keyword retry round {state['retry_round']}")
                        
                        await self._emit("search_progress", {
                            "batch_id": batch_id,
                            "status": "running",
                            "current_keyword": "expanding keywords...",
                            "leads_found": state["imported"],
                            "leads_target": limit,
                            "duplicates": state["duplicates"],
                            "scanned": state["raw_total"],
                            "retry_round": state["retry_round"],
                            "message": f"Expanding keywords (round {state['retry_round']})... Generating new search terms",
                        })
                        
                        # Generate additional keywords for each original keyword
                        new_keywords = []
                        for orig_kw in keywords:
                            additional = await self.strategy_engine.generate_additional_keywords(
                                original_keyword=orig_kw,
                                already_tried=list(all_tried_keywords),
                                location=location,
                                round_num=state["retry_round"],
                            )
                            new_keywords.extend(additional)
                        
                        # Deduplicate against everything we've tried
                        fresh_keywords = []
                        for kw in new_keywords:
                            if kw.lower() not in all_tried_keywords:
                                fresh_keywords.append(kw)
                                all_tried_keywords.add(kw.lower())
                        
                        if fresh_keywords:
                            print(f"[Discovery] Retry round {state['retry_round']}: {len(fresh_keywords)} new keywords: {fresh_keywords}")
                            
                            # Queue new keyword × provider combinations
                            for kw in fresh_keywords:
                                for provider in providers:
                                    await queue.put((kw, provider, location, 1, None))
                            
                            # Save new keywords to batch
                            async with self.db_lock:
                                for kw in fresh_keywords:
                                    kw_obj = LeadBatchKeyword(
                                        batch_id=batch_id,
                                        keyword=kw.strip(),
                                    )
                                    self.session.add(kw_obj)
                                await self.session.commit()
                        else:
                            # No new keywords could be generated
                            print(f"[Discovery] Retry round {state['retry_round']}: No new keywords generated")
                            stop_reason = "retries_exhausted"
                            max_reached.set()
                            break
                    else:
                        # Already exhausted all retry rounds
                        stop_reason = "retries_exhausted"
                        max_reached.set()
                        break
                
                # Check if queue is empty and no workers are running
                if queue.empty() and state["running"] == 0:
                    # Queue drained — check if we should retry or stop
                    if state["imported"] >= limit:
                        stop_reason = "target_achieved"
                        max_reached.set()
                        break
                    elif state["retry_round"] < MAX_RETRY_ROUNDS:
                        # Trigger a retry
                        retry_triggered.set()
                    else:
                        stop_reason = "providers_exhausted"
                        max_reached.set()
                        break

            max_reached.set()

            # Drain queue
            while not queue.empty():
                try:
                    queue.get_nowait()
                    queue.task_done()
                except asyncio.QueueEmpty:
                    break

            # Cancel workers immediately if user stopped
            if stop_reason == "user_stopped":
                for w in workers:
                    if not w.done():
                        w.cancel()

            await asyncio.gather(*workers, return_exceptions=True)

            # Final stop reason determination
            if not stop_reason:
                if state["imported"] >= limit:
                    stop_reason = "target_achieved"
                else:
                    stop_reason = "providers_exhausted"

            # 10. Finalize session
            await self._finalize_session(
                batch=batch,
                state=state,
                keyword_results=keyword_results,
                limit=limit,
                reason=stop_reason,
            )

            return batch_id

        except Exception as e:
            print(f"[Discovery] FAILED: {e}")
            traceback.print_exc()
            async with self.db_lock:
                batch.status = BatchStatus.FAILED.value
                batch.reason = "error"
                batch.completed_at = datetime.now(timezone.utc)
                await self.session.commit()

            await self._emit("search_failed", {
                "batch_id": batch_id,
                "error": str(e),
            })
            raise

    async def _finalize_session(
        self,
        batch: LeadBatch,
        state: dict,
        keyword_results: dict,
        limit: int,
        reason: str,
    ):
        """Finalize the search session — persist final stats and emit completion."""
        async with self.db_lock:
            for kw_obj in batch.keywords:
                kw_obj.results_found = keyword_results.get(kw_obj.keyword, 0)

            # Determine final status
            if batch.status in [BatchStatus.COMPLETED.value, BatchStatus.STOPPED.value]:
                final_status = batch.status
            elif reason == "target_achieved":
                final_status = BatchStatus.COMPLETED.value
            elif reason == "user_stopped":
                final_status = BatchStatus.STOPPED.value
            elif state["imported"] == 0:
                final_status = BatchStatus.FAILED.value
            else:
                final_status = BatchStatus.PARTIAL.value

            batch.status = final_status
            batch.reason = reason
            batch.raw_results_count = state["raw_total"]
            batch.duplicate_count = state["duplicates"]
            batch.rejected_count = state["rejected"]
            batch.final_count = state["imported"]
            batch.completed_at = datetime.now(timezone.utc)
            await self.session.commit()

        print(f"[Discovery] Complete: {state['imported']}/{limit} leads "
              f"(raw={state['raw_total']}, dup={state['duplicates']}, rej={state['rejected']}) "
              f"reason={reason} retries={state['retry_round']}")

        await self._emit("search_completed", {
            "batch_id": batch.id,
            "status": final_status,
            "reason": reason,
            "requested": limit,
            "raw_results": state["raw_total"],
            "duplicates": state["duplicates"],
            "rejected": state["rejected"],
            "final_count": state["imported"],
            "retry_rounds": state["retry_round"],
        })

    async def create_batch(
        self, keywords: list[str], location: str, limit: int
    ) -> LeadBatch:
        """Create a new batch with keywords (company-scoped)."""
        # Auto-generate batch name
        kw_summary = ", ".join(keywords[:3])
        if len(keywords) > 3:
            kw_summary += f" +{len(keywords) - 3}"
        now = datetime.now()
        name = f"{kw_summary} - {location} - {now.strftime('%d %b %Y %H:%M')}"

        batch = LeadBatch(
            company_id=self.company_id,
            name=name,
            location=location,
            requested_count=limit,
            status=BatchStatus.PENDING.value,
        )
        self.session.add(batch)
        await self.session.flush()

        # Save keywords
        for kw in keywords:
            kw_obj = LeadBatchKeyword(
                batch_id=batch.id,
                keyword=kw.strip(),
            )
            self.session.add(kw_obj)

        await self.session.commit()
        await self.session.refresh(batch)
        return batch

    def _normalize_result(self, raw, keyword: str, provider: str, location: str) -> dict:
        """Normalize a raw search result into lead data."""
        phone = raw.phone
        email = None
        snippet = raw.snippet or ""

        # Extract email from snippet
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
        if email_match:
            email = email_match.group(0)

        # Extract phone from snippet if missing
        if not phone:
            phone_match = re.search(r'(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}', snippet)
            if phone_match:
                extracted = phone_match.group(0).strip()
                if len(re.sub(r'\D', '', extracted)) >= 8:
                    phone = extracted

        return {
            "business_name": (raw.title or "").strip(),
            "website": raw.url,
            "phone": phone,
            "email": email,
            "address": raw.address,
            "source_url": raw.url,
            "city": location,
            "rating": raw.rating,
            "place_id": raw.place_id,
            "domain": raw.domain,
            "snippet": snippet,
        }

    def _validate_lead(self, data: dict) -> bool:
        """Validate a lead has minimum required data."""
        name = data.get("business_name", "").strip()
        if not name or name.lower() in ("unknown company", "unknown", ""):
            return False

        has_contact = bool(
            data.get("emails") or data.get("phones")
        )
        
        if not has_contact:
            data["quality_status"] = "suspect"
        else:
            data["quality_status"] = "valid"

        # Must have at least some web presence or location to be saved
        has_presence = bool(
            data.get("website") or data.get("domain") or data.get("address") or data.get("place_id") or has_contact
        )
        return has_presence

    def _compute_dedupe_key(self, data: dict) -> str:
        """Compute deterministic dedup key."""
        # Priority: place_id > domain > phone > name+city
        if data.get("place_id"):
            return f"place:{data['place_id']}"

        if data.get("domain"):
            domain = data["domain"].lower().strip()
            domain = re.sub(r'^www\.', '', domain)
            return f"domain:{domain}"

        if data.get("phone"):
            phone = re.sub(r'[\s\-\(\)\+]', '', data["phone"])
            if len(phone) >= 7:
                return f"phone:{phone}"

        # Fallback: name + city
        name = re.sub(r'[^a-z0-9]', '', data.get("business_name", "").lower())
        city = re.sub(r'[^a-z0-9]', '', data.get("city", "").lower())
        return f"name:{name}:{city}"

    async def _find_duplicate_in_batch(
        self, batch_id: str, dedupe_key: str, data: dict
    ) -> Lead | None:
        """Check for duplicates within the batch."""
        from sqlalchemy import select, or_, and_, func
        conditions = []

        if dedupe_key:
            conditions.append(Lead.dedupe_key == dedupe_key)
        if not conditions:
            name = data.get("business_name", "")
            city = data.get("city", "")
            if name and city:
                conditions.append(and_(
                    func.lower(Lead.business_name) == func.lower(name),
                    func.lower(Lead.city) == func.lower(city),
                ))

        if not conditions:
            return None

        stmt = (
            select(Lead)
            .where(Lead.batch_id == batch_id, or_(*conditions))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
