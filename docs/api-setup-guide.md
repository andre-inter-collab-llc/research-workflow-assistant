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

**Key type:** Email address (for polite pool)
**Required:** No, but strongly recommended
**Benefit:** Faster responses and higher rate limits via the "polite pool"

### How to configure

No API key is needed. Provide your email address so requests are routed through the polite pool:

```ini
OPENALEX_EMAIL=your@email.com
```

### Documentation

- [OpenAlex API docs](https://docs.openalex.org/)
- [Rate limits and polite pool](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication)

---

## Semantic Scholar

**Key type:** API Key
**Required:** No (works without, at lower rate limits)
**Without key:** ~100 requests/5 minutes
**With key:** Higher limits (varies by tier)

### How to get your key

1. Go to [Semantic Scholar API](https://www.semanticscholar.org/product/api)
2. Click "Request API Key"
3. Fill out the form describing your use case
4. You will receive an API key via email (may take a few business days)

### Configuration

```ini
S2_API_KEY=your_key_here
```

### Documentation

- [API docs](https://api.semanticscholar.org/api-docs/)
- [Getting started](https://www.semanticscholar.org/product/api)

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
| OpenAlex | No | Email (polite pool) | Yes (unlimited) | 10/sec polite pool |
| Semantic Scholar | No | API Key | Yes | ~100/5min without key |
| Europe PMC | No | None | Yes (unlimited) | Fair use |
| CrossRef | No | Email (polite pool) | Yes (unlimited) | Polite pool preferred |
| Zotero | Yes | API Key + User ID | Yes (300MB storage) | Fair use |

## Environment File Template

Create a `.env` file in the project root:

```ini
# PubMed / NCBI
NCBI_API_KEY=

# OpenAlex (email for polite pool)
OPENALEX_EMAIL=

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
