"""The prospecting pipeline: DISCOVER → PROFILE → (people, verification).

Each stage is independently runnable and independently re-runnable. That is
the point of the design, not an accident of it: profiling can re-run without
re-buying discovery, and discovery can widen without re-profiling everyone.

What chains them is a *query*, not a hand-off. PROFILE asks the database
"which companies have I not looked at, or not looked at lately?" rather than
being handed a list by DISCOVER. So a profile run started for any reason
picks up whatever discovery left behind, a crashed run resumes by itself, and
re-observing on a schedule turns the same signal into a time series.

Segment before you enrich: enrichment cost scales with list size and
conversion does not, so profile the businesses you would actually contact,
not every row you hold.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("harvey.pipeline")

# How long a profile observation stays fresh. Re-reading a site every quarter
# is what makes "they dropped their agency" a visible event.
PROFILE_STALE_DAYS = 90


@dataclass
class PipelineReport:
    """What a full pass did, stage by stage."""

    discover: dict | None = None
    profiled_companies: int = 0
    profile_observations: int = 0
    profile_run_id: str = ""
    skipped: str = ""
    errors: list[str] = field(default_factory=list)
    email_summary: dict = field(default_factory=dict)
    target_summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "discover": self.discover,
            "profiled_companies": self.profiled_companies,
            "profile_observations": self.profile_observations,
            "profile_run_id": self.profile_run_id,
            "skipped": self.skipped,
            "errors": self.errors, "email_summary": self.email_summary, "target_summary":self.target_summary,
        }

    def summary_line(self) -> str:
        parts = []
        if self.discover:
            parts.append(f"{self.discover.get('new_companies', 0)} new companies")
        if self.profiled_companies:
            parts.append(f"{self.profiled_companies} profiled "
                         f"({self.profile_observations} observations)")
        return ", ".join(parts) or "nothing to do"


async def run_profile_stage(
    state,
    limit: int = 100,
    stale_days: int = PROFILE_STALE_DAYS,
    on_progress=None,
) -> tuple[int, int, str]:
    """Profile whatever currently needs it.

    Returns (companies, observations, run_id). Free — three HTTP requests per
    business, no browser, no model call — so it is safe to run on every
    heartbeat without touching the Claude budget.
    """
    from harvey.collectors.profile import profile_companies

    pending = await state.companies_needing_profile(limit=limit,
                                                    stale_days=stale_days)
    if on_progress:
        await on_progress({'stage': 'profiling', 'total': len(pending), 'completed': 0, 'current': ''})
    if not pending:
        return 0, 0, ""

    logger.info("profile: %d companies need a look", len(pending))
    processed = 0
    async def tracked(event):
        nonlocal processed
        processed = event.get('completed', processed)
        await on_progress(event)
    observations, run_id = await profile_companies(state, pending, **({'on_progress': tracked} if on_progress else {}))
    return processed if on_progress else len(pending), observations, run_id


async def run_prospecting(
    state,
    config,
    provider: str | None = None,
    queries=None,
    max_spend: float = 1.0,
    profile: bool = True,
    profile_limit: int = 200,
    dry_run: bool = False,
    on_progress=None,
    radius_km=None,
    email_search=False,
    email_mode="quick",
    target_profile=None,
) -> PipelineReport:
    """Discover businesses, then read what their websites say about them.

    The two stages are deliberately not coupled through a list: profiling
    queries the database for what needs attention, so it also sweeps up
    anything an earlier run left unfinished.
    """
    from harvey.collectors.discover import DEFAULT_PROVIDER, run_discovery

    report = PipelineReport()

    discovery = await run_discovery(
        state, config, provider or DEFAULT_PROVIDER, queries,
        max_spend=max_spend, dry_run=dry_run,
        **({'on_progress': on_progress, 'radius_km': radius_km} if on_progress or radius_km else {}),
    )
    report.discover = discovery.as_dict()
    report.errors.extend(discovery.errors)

    if dry_run:
        report.skipped = "dry run"
        return report
    if not profile and not email_search and not target_profile:
        report.skipped = "profiling skipped"
        return report

    if discovery.stopped or await state.get_setting('discovery_paused'):
        report.skipped = discovery.stopped or 'paused'
        return report

    # Profile runs even when discovery found nothing new: a previous run may
    # have been interrupted, and observations go stale on a schedule.
    if profile:
        try:
            companies, observations, run_id = await run_profile_stage(
                state, limit=profile_limit, **({'on_progress': on_progress} if on_progress else {}))
            report.profiled_companies = companies
            report.profile_observations = observations
            report.profile_run_id = run_id
        except Exception as e:
            logger.exception("profile stage failed")
            report.errors.append(f"profile: {e}")

    if target_profile:
        from harvey.target_profiles import evaluate_profile
        ids=list(dict.fromkeys((report.discover or {}).get('company_ids',[])))
        report.target_summary=await evaluate_profile(state,target_profile,company_ids=ids)
        if on_progress:
            await on_progress({'target_summary':report.target_summary})

    if email_search:
        from harvey.collectors.company_contacts import lookup_company_emails
        import asyncio
        ids = list(dict.fromkeys((report.discover or {}).get('company_ids', [])))
        summary = {'total': min(len(ids),1000), 'done':0, 'found':0, 'not_found':0,
                   'no_website':0, 'failed':0, 'skipped_limit':max(0,len(ids)-1000), 'stopped':False}
        report.email_summary = summary
        if on_progress:
            await on_progress({'stage':'emails','total':summary['total'],'completed':0,'current':'','email_summary':dict(summary)})
        for company_id in ids[:1000]:
            if await state.get_setting('discovery_paused'):
                summary['stopped'] = True
                break
            company = await state.get_company(company_id)
            if on_progress:
                await on_progress({'current':company.name if company else ''})
            try:
                result = await asyncio.wait_for(lookup_company_emails(company,state,mode=email_mode),
                    timeout=80 if email_mode == 'thorough' else 25) if company else {'status':'failed'}
                status = result['status']
                status = status if status in ('found','not_found','no_website') else 'failed'
            except Exception:
                status = 'failed'
            summary[status] += 1
            summary['done'] += 1
            if status == 'failed':
                report.errors.append(f'email lookup failed: {company_id}')
            if on_progress:
                await on_progress({'completed':summary['done'],'email_summary':dict(summary),
                                   **({'error':True} if status == 'failed' else {})})
    return report
