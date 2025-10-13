# DreamHack Wargame Crawler

A comprehensive Python crawler for DreamHack wargame challenges that automatically discovers, catalogs, and downloads challenges while maintaining accurate local tracking with flexible sorting capabilities.

## Overview

This tool provides complete automation for discovering and managing DreamHack wargame challenges. It systematically crawls all challenge combinations, maintains accurate metadata, prevents duplicate downloads, and offers flexible sorting options for the generated manifest.

## Key Features

**Complete Challenge Discovery**

- Crawls all combinations of category, difficulty, and status parameters
- Systematic pagination across all parameter combinations
- Accurate metadata extraction including titles, categories, difficulties, and descriptions

**Smart Download Management**

- Prevents duplicate downloads through intelligent tracking
- Local file synchronization with manifest updates
- Automatic detection of successfully downloaded challenges
- Structured file organization by category

**Flexible Manifest Sorting**

- Sort by challenge ID, title, category, difficulty, or download status
- Ascending or descending order options
- Option to disable sorting entirely
- Automatic application during all manifest updates

**Robust Operation**

- Multiple parsing strategies for different page layouts
- Automatic retry with exponential backoff on failures
- Fallback to Playwright for JavaScript-heavy pages
- Comprehensive error handling and logging

## Installation

### Requirements

- Python 3.7+
- Required packages: `requests`, `beautifulsoup4`, `lxml`
- Optional: `playwright` (for JavaScript-heavy pages)

### Setup

```bash
# Clone or download the script
git clone <repository-url>
cd Dreamhack_Wargame_Crawler

# Install required packages
pip install requests beautifulsoup4 lxml

# Optional: Install Playwright for enhanced compatibility
pip install playwright
playwright install chromium
```

## Basic Usage

### 1. Crawl All Challenges

```bash
# Basic crawl with default settings
python3 dreamhack_crawler.py

# With verbose output
python3 dreamhack_crawler.py --verbose

# With authentication for member-only challenges
python3 dreamhack_crawler.py --cookie "sessionid=abc123" --verbose
```

### 2. Update Local Tracking

```bash
# Sync manifest with downloaded files
python3 dreamhack_crawler.py --update --verbose
```

### 3. Download Specific Challenge

```bash
# Download by challenge ID
python3 dreamhack_crawler.py --download 1234 --verbose
```

## Sorting Options

The crawler supports flexible sorting of the manifest file:

### Sort by Challenge ID

```bash
# Newest challenges first (default)
python3 dreamhack_crawler.py --update --sort-by id --sort-order desc

# Oldest challenges first
python3 dreamhack_crawler.py --update --sort-by id --sort-order asc
```

### Sort by Title

```bash
# Alphabetical order (A-Z)
python3 dreamhack_crawler.py --update --sort-by title --sort-order asc

# Reverse alphabetical (Z-A)
python3 dreamhack_crawler.py --update --sort-by title --sort-order desc
```

### Sort by Category

```bash
# Group by category (A-Z)
python3 dreamhack_crawler.py --update --sort-by category --sort-order asc
```

### Sort by Difficulty

```bash
# Easiest first
python3 dreamhack_crawler.py --update --sort-by difficulty --sort-order asc

# Hardest first
python3 dreamhack_crawler.py --update --sort-by difficulty --sort-order desc
```

### Sort by Download Status

```bash
# Show downloaded challenges first
python3 dreamhack_crawler.py --update --sort-by has_download --sort-order desc
```

### Disable Sorting

```bash
# Keep original order
python3 dreamhack_crawler.py --update --sort-by none
```

## Command Line Options

| Argument | Default | Description |
|----------|---------|-------------|
| `--base` | `https://dreamhack.io/wargame` | Base URL for the wargame site |
| `--cookie` | None | Session cookie string for authentication |
| `--delay` | `1.0` | Delay between requests in seconds |
| `--download` | None | Download specific challenge by ID |
| `--update` | False | Update local tracking based on downloaded files |
| `--output` | `manifest.json` | Output manifest file path |
| `--verbose`, `-v` | False | Enable verbose output |
| `--sort-by` | `id` | Sort criteria: `none`, `id`, `title`, `category`, `difficulty`, `first_seen`, `last_seen`, `has_download` |
| `--sort-order` | `desc` | Sort order: `asc` (ascending) or `desc` (descending) |

## Output Structure

### Manifest File (manifest.json)

The crawler creates a comprehensive JSON manifest with the following structure:

```json
{
  "1234": {
    "id": "1234",
    "title": "Challenge Name",
    "challenge_url": "https://dreamhack.io/wargame/challenges/1234",
    "category": "web",
    "difficulty": "2",
    "has_download": false,
    "description": "Challenge description text",
    "first_seen": "2025-10-13T02:11:26.963000+00:00",
    "last_seen": "2025-10-13T02:11:26.963000+00:00"
  }
}
```

### Directory Structure for Downloads

```
challenges/
├── web/
│   ├── 1234-Challenge_Name/
│   │   ├── file1.zip
│   │   ├── file2.txt
│   │   └── meta.json
│   └── 1235-Another_Challenge/
├── crypto/
│   └── 1236-Crypto_Challenge/
└── pwnable/
    └── 1237-Binary_Challenge/
```

### Download Metadata (meta.json)

Each downloaded challenge includes a metadata file:

```json
{
  "id": 1234,
  "files": [
    {
      "filename": "challenge.zip",
      "url_fetched": "https://example.s3.amazonaws.com/file",
      "checksum": "sha256_hash",
      "downloaded_at": "2025-10-13T03:00:00.000000+00:00"
    }
  ]
}
```

## Workflow Examples

### Complete Setup from Scratch

```bash
# 1. Initial crawl to discover all challenges
python3 dreamhack_crawler.py --verbose

# 2. Download a specific challenge
python3 dreamhack_crawler.py --download 1234 --verbose

# 3. Update tracking after manual file operations
python3 dreamhack_crawler.py --update --verbose

# 4. Re-sort manifest by difficulty
python3 dreamhack_crawler.py --update --sort-by difficulty --sort-order asc --verbose
```

### Maintenance Workflow

```bash
# 1. Update catalog with new challenges
python3 dreamhack_crawler.py --verbose

# 2. Sync local tracking
python3 dreamhack_crawler.py --update --verbose

# 3. Sort by newest first
python3 dreamhack_crawler.py --update --sort-by id --sort-order desc --verbose
```

### Category-Specific Analysis

```bash
# Sort by category to group related challenges
python3 dreamhack_crawler.py --update --sort-by category --sort-order asc --verbose

# Then sort by difficulty within categories
python3 dreamhack_crawler.py --update --sort-by difficulty --sort-order asc --verbose
```

## Technical Details

### Crawling Strategy

- **Comprehensive Parameter Coverage**: Iterates through all combinations of:
  - Categories: `""` (all), `misc`, `crypto`, `web`, `web3`, `pwnable`, `forensics`, `reversing`, `cloud`
  - Difficulties: `""` (all), `0`, `beginner`, `1-10`
  - Statuses: `""` (all), `todo`, `attempted`, `solved`
  - Pages: Starting from 1, continues until empty results

### Error Handling

- **Request Failures**: Automatic retry with exponential backoff
- **Parsing Errors**: Graceful handling with detailed logging
- **Network Issues**: Fallback to Playwright for JavaScript-heavy pages
- **Invalid Data**: Safe handling of missing or malformed challenge data

### Performance Considerations

- **Rate Limiting**: Configurable delays prevent server overload
- **Incremental Processing**: Only fetches details for new challenges
- **Memory Efficiency**: Processes challenges in batches
- **Periodic Saves**: Regular manifest updates prevent data loss

### Download Safety

- **Duplicate Prevention**: Checks `has_download` flag before downloading
- **URL Validation**: Sanitizes and validates download URLs
- **Checksum Verification**: SHA256 hashes for file integrity
- **Atomic Operations**: Safe file operations with proper error handling

## Troubleshooting

### Common Issues

**Issue**: No challenges found during crawling

- **Solution**: Check internet connection and base URL
- **Solution**: Try with authentication cookie if challenges require login

**Issue**: Download fails with 403 errors

- **Solution**: Provide valid session cookie with `--cookie`
- **Solution**: Increase delay with `--delay 2.0` to avoid rate limiting

**Issue**: JavaScript-heavy pages not loading

- **Solution**: Install Playwright: `pip install playwright && playwright install chromium`

**Issue**: Manifest not sorting correctly

- **Solution**: Check that sort parameters are correct
- **Solution**: Run update command to apply sorting: `--update --sort-by id --sort-order desc`

### Debug Information

Use `--verbose` flag to get detailed logging:

- Request URLs and response codes
- Number of challenges found per page
- Download progress and file information
- Sorting operations and results

### File Recovery

If manifest file is corrupted:

1. Backup the corrupted file
2. Run `--update` to rebuild from downloaded files
3. Re-run crawling to restore missing data

## Contributing

### Code Structure

- `DreamHackCrawler`: Main crawler class
- `crawl_mapping_mode()`: Comprehensive challenge discovery
- `download_challenge()`: Individual challenge download
- `update_local_tracking()`: Sync with local files
- `save_manifest()`: Flexible sorting and file output

### Adding New Features

1. Sorting criteria: Add new options to `_sort_manifest()`
2. Download sources: Extend `_extract_download_urls()`
3. Challenge parsing: Enhance `parse_challenges_from_listing()`

## License

This project is intended for educational purposes and responsible security research. Users must comply with DreamHack's terms of service and applicable laws.

## Version History

- **v2.0**: Added comprehensive parameter crawling, flexible sorting, and improved local tracking
- **v1.0**: Basic challenge discovery and download functionality

---

For questions or issues, please review the troubleshooting section or check the verbose output for detailed error information.
