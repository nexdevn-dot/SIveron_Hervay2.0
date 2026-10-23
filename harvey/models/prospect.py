"""Contact data model — a person at a company."""

from datetime import datetime, timezone

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    """Naive UTC now (consistent with DB storage; avoids deprecated utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Prospect(BaseModel):
    revision: int = 0
    do_not_contact: bool = False
    block_reason: str = ""
    blocked_at: str = ""
    contact_type: Literal["person", "company"] = "person"
    id: str = ""
    company_id: str = ""       # FK to companies table
    first_name: str = ""       # required for a valid contact
    last_name: str = ""        # required for a valid contact
    email: str = ""
    email_verified: bool = False
    # verified / risky (catch-all) / guess (never auto-sent) / invalid / ""
    email_status: str = ""
    phone: str = ""
    phone_verified: bool = False
    linkedin_url: str = ""
    title: str = ""            # required for a valid contact
    seniority: str = ""        # c_suite, vp, director, manager, individual
    department: str = ""
    source: str = ""           # how we found them
    source_found_at: str = ""
    source_url: str = ""       # where we found the info
    status: str = "new"        # new/contacted/replied/meeting/closed/lost
    score: int = 0
    personalization_notes: str = ""
    # legacy fields kept for backwards compat with existing code
    company: str = ""
    industry: str = ""
    company_size: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        """Emails are dedup keys — normalize so 'Jane@X.com' == 'jane@x.com'."""
        return (v or "").strip().lower()

    @field_validator("linkedin_url")
    @classmethod
    def _strip_linkedin(cls, v: str) -> str:
        return (v or "").strip()

    def full_name(self) -> str:
        return self.company if self.contact_type == "company" else f"{self.first_name} {self.last_name}".strip()

    def is_valid(self) -> bool:
        """A contact must have at minimum a name and title."""
        return self.contact_type == "person" and bool(self.first_name and self.last_name and self.title)
