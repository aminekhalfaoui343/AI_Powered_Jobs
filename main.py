"""
AI-Powered Job Market Scraping — demo CLI

Usage:
    python main.py "https://candidat.francetravail.fr/offres/recherche/detail/213CLSZ"
    python main.py "JOB_URL" --scrape-only

Pipeline:
    URL -> scraper (Stage A) -> RawJobPosting -> OpenRouter (Stage B) -> JobPosting
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import ValidationError
from requests import HTTPError, RequestException, Timeout
from rich.console import Console
from rich.panel import Panel

from pipeline.run import extract_job, run_pipeline, scrape_job
from scrapers.registry import list_supported_sources

load_dotenv()

console = Console()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(name)s | %(message)s",
    )


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url!r}")


def print_raw_job(raw_job) -> None:
    preview = raw_job.raw_text[:400] + ("..." if len(raw_job.raw_text) > 400 else "")
    console.print(Panel(
        f"[bold]Source:[/bold] {raw_job.source}\n"
        f"[bold]URL:[/bold] {raw_job.url}\n"
        f"[bold]Title (scraped):[/bold] {raw_job.title or 'None'}\n"
        f"[bold]Company (scraped):[/bold] {raw_job.company or 'None'}\n"
        f"[bold]Location (scraped):[/bold] {raw_job.location or 'None'}\n\n"
        f"[bold]Raw text preview:[/bold]\n{preview}",
        title="Stage A — RawJobPosting",
        border_style="yellow",
    ))


def print_job_posting(job) -> None:
    console.print(Panel(
        f"[bold cyan]JobPosting[/bold cyan]\n\n"
        f"title={job.title!r},\n"
        f"company={job.company!r},\n"
        f"location={job.location!r},\n"
        f"description={job.description!r},\n"
        f"skills={job.skills!r},\n"
        f"experience={job.experience!r},\n"
        f"education={job.education!r},\n"
        f"salary={job.salary!r},\n"
        f"contract_type={job.contract_type!r}",
        title=f"Stage B — Structured Output",
        border_style="green",
    ))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape a job URL and extract structured data with OpenRouter.",
    )
    parser.add_argument("url", help="Direct URL of a job posting detail page")
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Run Stage A only (no LLM extraction). Useful to test scrapers.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        validate_url(args.url)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    console.print("\n[bold]Supported sources (initial):[/bold]", ", ".join(list_supported_sources()))
    console.print(f"[bold]Target URL:[/bold] {args.url}\n")

    try:
        if args.scrape_only:
            raw_job = scrape_job(args.url)
            print_raw_job(raw_job)
            console.print("[green]Scrape-only mode complete.[/green]")
            return 0

        raw_job, job = asyncio.run(run_pipeline(args.url))
        print_raw_job(raw_job)
        print_job_posting(job)
        return 0

    except ValueError as exc:
        console.print(f"[red]Configuration / data error:[/red] {exc}")
        return 1
    except HTTPError as exc:
        console.print(f"[red]HTTP error:[/red] {exc}")
        return 1
    except Timeout:
        console.print("[red]Request timed out.[/red]")
        return 1
    except RequestException as exc:
        console.print(f"[red]Network error:[/red] {exc}")
        return 1
    except ValidationError as exc:
        console.print(f"[red]Invalid structured output from LLM:[/red]\n{exc}")
        return 1
    except Exception as exc:
        console.print(f"[red]Unexpected error:[/red] {exc}")
        if args.verbose:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
