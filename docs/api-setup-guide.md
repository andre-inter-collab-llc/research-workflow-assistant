# API Setup Guide

This guide explains how to obtain API keys and credentials for each academic database used by the research-workflow-assistant.

## PubMed / NCBI E-utilities

**Key type:** NCBI API Key
**Required:** Recommended (works without, but rate-limited to 3 requests/second)
**With key:** 10 requests/second

### How to get your key

1. Go to [NCBI](https://www.ncbi.nlm.nih.gov/) and create an account (or sign in)
2. Click your username in the top-right corner, then select "Account settings"
3. Scroll to "API Key Management"
4. Click "Create an API Key"
5. Copy the generated key

### Configuration

```ini
NCBI_API_KEY=your_key_here
```

### Documentation

- [NCBI E-utilities docs](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [Usage guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/#chapter2.Usage_Guidelines_and_Requiremen)

---

## OpenAlex

**Key type:** API Key (free)
**Required:** Yes (free key gives $1/day of API usage)
**Rate limit:** 100 requests/second; $1/day free budget covers ~1,000 searches or ~10,000 list/filter calls

### How to get your key

1. Go to [OpenAlex](https://openalex.org/) and create a free account
2. Navigate to [API Key Settings](https://openalex.org/settings/api-key)
3. Copy your API key

### Configuration

```ini
OPENALEX_API_KEY=your_key_here
```

### Free tier daily budget

Your free key gives you $1/day to spend across API operations:

| Operation | Cost per call | Free daily allowance |
|-----------|--------------|---------------------|
| Get single entity (by ID/DOI) | Free | Unlimited |
| List + filter | $0.0001 | ~10,000 calls |
| Search (full-text) | $0.001 | ~1,000 calls |
| Semantic search | $0.01 | ~100 calls |

Monitor usage at [openalex.org/settings/usage](https://openalex.org/settings/usage) or via the `/rate-limit` endpoint.

### Documentation

- [OpenAlex Developer Docs](https://developers.openalex.org/)
- [Authentication & Pricing](https://developers.openalex.org/api-reference/authentication)
- [API Reference](https://developers.openalex.org/api-reference/introduction)

---

## Semantic Scholar

**Key type:** API Key
**Required:** No (works without, at lower rate limits)
**Rate plans:** Two tiers — 1 req/sec (unauthenticated) and higher with API key
**Key inactivity:** Keys inactive for ~60 days may be revoked

### How to get your key

1. First, verify you can make unauthenticated requests (the server works without a key at 1 req/sec)
2. Go to the [Semantic Scholar API key request form](https://www.semanticscholar.org/product/api#api-key-form)
3. Fill out the form describing your use case and expected endpoints
4. Complete the [API License Agreement](https://www.semanticscholar.org/product/api/license)
5. You will receive an API key via email (may take a few business days)

### Configuration

```ini
S2_API_KEY=your_key_here
```

### License requirements

By using the Semantic Scholar API, you agree to the [API License Agreement](https://www.semanticscholar.org/product/api/license). Key obligations:

- **Attribution**: Include attribution to "Semantic Scholar" in any published materials that use S2 data
- **Citation**: Cite [The Semantic Scholar Open Data Platform](https://www.semanticscholar.org/paper/cb92a7f9d9dbcf9145e32fdfa0e70e2a6b828eb1) in scientific publications that use API results
- **Rate limits**: Do not attempt to exceed or circumvent rate limits
- **Exponential backoff**: Apply exponential backoff on 429 responses (implemented in the MCP server)
- **Key security**: Do not share your API key beyond authorized users in your organization

### Documentation

- [API docs](https://api.semanticscholar.org/api-docs/)
- [API overview](https://www.semanticscholar.org/product/api)
- [API tutorial](https://www.semanticscholar.org/product/api/tutorial) — step-by-step guide covering keyword search, recommendations, author lookups, bulk search, dataset downloads, and query syntax
- [License agreement](https://www.semanticscholar.org/product/api/license)

---

## Europe PMC

**Key type:** None required
**Required:** No authentication needed
**Rate limits:** Fair use; be respectful with request frequency

### Configuration

No configuration needed. The Europe PMC server works out of the box.

### Documentation

- [Europe PMC REST API](https://europepmc.org/RestfulWebService)
- [Article search](https://europepmc.org/searchsyntax)

---

## CrossRef

**Key type:** Email address (for polite pool)
**Required:** No, but strongly recommended
**Benefit:** Faster responses via the "polite pool"

### How to configure

Provide your email address:

```ini
CROSSREF_EMAIL=your@email.com
```

For projects with heavy usage, consider registering for the [CrossRef Plus service](https://www.crossref.org/services/metadata-retrieval/).

### Documentation

- [CrossRef REST API](https://api.crossref.org/)
- [API docs](https://api.crossref.org/swagger-ui/index.html)

---

## Zotero

**Key type:** API Key + User ID
**Required:** Yes (for Zotero integration)

### How to get your credentials

1. Go to [Zotero Settings](https://www.zotero.org/settings/keys)
2. Log in (create an account if needed)
3. Click "Create new private key"
4. Give it a description (e.g., "research-workflow-assistant")
5. Under "Personal Library," check:
   - Allow library access
   - Allow write access
   - Allow notes access
6. Click "Save Key"
7. Copy the generated key

To find your User ID:

1. Go to [Zotero Settings](https://www.zotero.org/settings/keys)
2. Your numeric User ID is displayed at the top of the page

### Configuration

```ini
ZOTERO_API_KEY=your_key_here
ZOTERO_USER_ID=your_numeric_user_id
```

### Working with group libraries

If you need to access a group library instead of your personal library, set the group ID:

```ini
ZOTERO_GROUP_ID=your_group_id
```

Find group IDs at: `https://www.zotero.org/groups/`

### Documentation

- [Zotero Web API v3](https://www.zotero.org/support/dev/web_api/v3/start)
- [API key permissions](https://www.zotero.org/support/dev/web_api/v3/basics)

---

## Summary Table

| Service | Auth Required | Key Type | Free Tier | Rate Limit |
|---------|:---:|----------|-----------|------------|
| PubMed | Recommended | API Key | Yes (unlimited) | 3/sec without key, 10/sec with key |
| OpenAlex | Yes (free) | API Key | $1/day free | 100/sec, $1/day budget |
| Semantic Scholar | No | API Key | Yes (1 req/sec) | 1 req/sec unauthenticated |
| Europe PMC | No | None | Yes (unlimited) | Fair use |
| CrossRef | No | Email (polite pool) | Yes (unlimited) | Polite pool preferred |
| Zotero | Yes | API Key + User ID | Yes (300MB storage) | Fair use |

## Environment File Template

Create a `.env` file in the project root:

```ini
# PubMed / NCBI
NCBI_API_KEY=

# OpenAlex (free API key required)
OPENALEX_API_KEY=

# Semantic Scholar (optional, for higher rate limits)
S2_API_KEY=

# CrossRef (email for polite pool)
CROSSREF_EMAIL=

# Zotero (required for reference management)
ZOTERO_API_KEY=
ZOTERO_USER_ID=

# Tracking directories (optional, defaults to ./review-tracking and ./project-tracking)
PRISMA_PROJECT_DIR=
PROJECT_TRACKER_DIR=
```
