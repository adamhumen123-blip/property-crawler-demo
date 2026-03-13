# PropertyCrawler

A Python-based tool that scrapes property listing pages and discovers contact information for property owners.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Basic run
python property_crawler.py --input urls.csv --output results.csv

# With API keys for better results
python property_crawler.py \
  --input urls.csv \
  --output results.csv \
  --serpapi-key YOUR_KEY \
  --vision-key YOUR_GOOGLE_KEY

# Skip image search (faster)
python property_crawler.py --input urls.csv --no-images
```

## Input CSV Format
```
url
https://www.airbnb.com/rooms/12345678
https://www.vrbo.com/1234567
```

## Output Columns
| Column | Description |
|---|---|
| listing_url | Original URL |
| title | Listing title |
| host_name | Host/manager name |
| location | City/area |
| description | Property description excerpt |
| photo_urls | Pipe-separated photo URLs |
| address | Discovered property address |
| owner_name | Discovered owner name |
| management_co | Management company |
| email | Contact email |
| phone | Contact phone |
| contact_source | URL where contact was found |
| img_match_count | Number of image match sources |
| img_match_sources | Pipe-separated match domains |

## Architecture
```
urls.csv
   ↓
ListingScraper (Playwright)
   → title, host, location, description, photo_urls
   ↓
ReverseImageSearch (Google Vision + Bing)
   → img_match_sources
   ↓
ContactEnricher (SerpAPI + DuckDuckGo + scraping)
   → email, phone, address, owner_name
   ↓
results.csv / results.json
```
