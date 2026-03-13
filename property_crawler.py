"""
PropertyCrawler — Listing Intelligence Pipeline
Usage: python property_crawler.py --input urls.csv --output results.csv
"""
import asyncio
import argparse
import csv
import json
import logging
from pathlib import Path
import pandas as pd
from playwright.async_api import async_playwright
from modules.scraper import ListingScraper
from modules.enricher import ContactEnricher
from modules.image_search import ReverseImageSearch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("PropertyCrawler")

async def run_pipeline(urls: list[str], config: dict) -> list[dict]:
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )

        scraper = ListingScraper(context)
        enricher = ContactEnricher(serpapi_key=config.get("serpapi_key"))
        img_searcher = ReverseImageSearch(google_vision_key=config.get("vision_key"))

        for i, url in enumerate(urls):
            log.info(f"[{i+1}/{len(urls)}] Processing: {url}")
            try:
                # STEP 1: Scrape listing
                listing = await scraper.extract(url)
                log.info(f"  ✓ Scraped: {listing.get('title', 'Unknown')[:60]}")

                # STEP 2: Reverse image search
                if config.get("reverse_image") and listing.get("photo_urls"):
                    matches = await img_searcher.search_all(listing["photo_urls"][:3])
                    listing["image_matches"] = matches
                    log.info(f"  ✓ Image matches: {len(matches)} sources found")

                # STEP 3: Contact enrichment
                if config.get("enrich_contacts"):
                    contacts = await enricher.find_contacts(listing)
                    listing.update(contacts)
                    if contacts.get("email") or contacts.get("phone"):
                        log.info(f"  ✓ Contact found: {contacts.get('email', '')} {contacts.get('phone', '')}")
                    else:
                        log.warning("  ⚠ No contact information discovered")

                results.append(listing)

            except Exception as e:
                log.error(f"  ✗ Failed to process {url}: {e}")
                results.append({"url": url, "error": str(e)})

        await browser.close()

    return results


def load_urls(path: str) -> list[str]:
    if path.endswith(".csv"):
        df = pd.read_csv(path)
        col = next((c for c in df.columns if "url" in c.lower()), df.columns[0])
        return df[col].dropna().tolist()
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def save_results(results: list[dict], output_path: str):
    flat = []
    for r in results:
        row = {
            "listing_url":      r.get("url", ""),
            "title":            r.get("title", ""),
            "host_name":        r.get("host", ""),
            "location":         r.get("location", ""),
            "description":      r.get("description", "")[:500],
            "photo_urls":       " | ".join(r.get("photo_urls", [])[:5]),
            "address":          r.get("address", ""),
            "owner_name":       r.get("owner_name", ""),
            "management_co":    r.get("management_company", ""),
            "email":            r.get("email", ""),
            "phone":            r.get("phone", ""),
            "contact_source":   r.get("contact_source_url", ""),
            "img_match_count":  len(r.get("image_matches", [])),
            "img_match_sources": " | ".join(r.get("image_matches", [])[:5]),
            "error":            r.get("error", ""),
        }
        flat.append(row)

    df = pd.DataFrame(flat)
    if output_path.endswith(".json"):
        df.to_json(output_path, orient="records", indent=2)
    else:
        df.to_csv(output_path, index=False)
    log.info(f"Results saved → {output_path} ({len(flat)} records)")


async def main():
    parser = argparse.ArgumentParser(description="PropertyCrawler Pipeline")
    parser.add_argument("--input",   required=True, help="CSV or TXT file with listing URLs")
    parser.add_argument("--output",  default="results.csv", help="Output CSV/JSON path")
    parser.add_argument("--no-images",   action="store_true", help="Skip reverse image search")
    parser.add_argument("--no-enrich",   action="store_true", help="Skip contact enrichment")
    parser.add_argument("--serpapi-key", default=None)
    parser.add_argument("--vision-key",  default=None)
    args = parser.parse_args()

    urls = load_urls(args.input)
    log.info(f"Loaded {len(urls)} URLs from {args.input}")

    config = {
        "reverse_image":    not args.no_images,
        "enrich_contacts":  not args.no_enrich,
        "serpapi_key":      args.serpapi_key,
        "vision_key":       args.vision_key,
    }

    results = await run_pipeline(urls, config)
    save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
