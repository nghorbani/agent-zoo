"""Offline checks of the data models the job-listing agents exchange."""

import pytest
from pydantic import ValidationError

from agent_zoo.get_job_listings.get_company_url import CompanyUrlResponse
from agent_zoo.get_job_listings.get_job_listings import Job, JobListings, Link, PageExtractionResult, PaginationInfo


def test_page_extraction_result_round_trips():
    result = PageExtractionResult(
        links=[Link(title="Data Engineer", url="https://example.com/jobs/1")],
        pagination_info=PaginationInfo(current_page=1, total_pages=3, next_page_url="https://example.com/jobs?page=2", has_next_page=True),
    )

    restored = PageExtractionResult.model_validate(result.model_dump())

    assert restored == result
    assert restored.pagination_info.next_page_url.endswith("page=2")


def test_link_requires_a_url():
    with pytest.raises(ValidationError):
        Link(title="no url")


def test_job_listings_hold_jobs():
    job = Job(
        title="Data Engineer",
        location="Ulm",
        url="https://example.com/jobs/1",
        description="Build pipelines.",
        date_posted="2026-09-17",
        skills_required=["python", "sql"],
        employment_type="full-time",
    )
    listings = JobListings(jobs=[job])

    assert listings.jobs[0].skills_required == ["python", "sql"]


def test_company_url_response_fields():
    response = CompanyUrlResponse(
        company_name="Cubert", city="Ulm", country="Germany",
        official_url="https://cubert-hyperspectral.com/", confidence=0.9, validation_notes="top hit",
    )

    assert response.official_url.startswith("https://")
