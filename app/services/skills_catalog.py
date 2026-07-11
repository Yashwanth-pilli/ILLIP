"""
Agent Skills Directory — a curated, browsable index of real agent skills,
seeded from VoltAgent/awesome-agent-skills (1,497+ skills across the ecosystem).

This is a DISCOVERY directory, not an auto-installer: most of these are external
Claude/MCP skills or best-practice packs that live in their own repos. ILLIP lists
them so a user can search + find the right capability, then follow the link. The
runnable, keyless HTTP tools live separately in the Plugins catalogue.

Users can extend this with data/skills_directory.json (same shape) — merged on top.
"""

from __future__ import annotations

import json
from pathlib import Path

_SOURCE = "https://github.com/VoltAgent/awesome-agent-skills"

# Curated subset of the most useful, well-known skills. (name, provider, desc, category)
_SEED: list[dict] = [
    # Documents & content
    {"name": "docx", "provider": "anthropic", "category": "documents", "description": "Create, edit, and analyze Word documents"},
    {"name": "pptx", "provider": "anthropic", "category": "documents", "description": "Create, edit, and analyze PowerPoint presentations"},
    {"name": "xlsx", "provider": "anthropic", "category": "documents", "description": "Create, edit, and analyze Excel spreadsheets"},
    {"name": "pdf", "provider": "anthropic", "category": "documents", "description": "Extract text, create PDFs, and handle forms"},
    # Design & frontend
    {"name": "frontend-design", "provider": "anthropic", "category": "design", "description": "Frontend design and UI/UX development tools"},
    {"name": "canvas-design", "provider": "anthropic", "category": "design", "description": "Design visual art in PNG and PDF formats"},
    {"name": "figma-implement-design", "provider": "figma", "category": "design", "description": "Translate Figma designs into production code"},
    {"name": "shadcn-ui", "provider": "google-labs-code", "category": "design", "description": "Build UI components with shadcn/ui"},
    # Web & browser
    {"name": "webapp-testing", "provider": "anthropic", "category": "web", "description": "Test local web applications using Playwright"},
    {"name": "playwright", "provider": "openai", "category": "web", "description": "Automate real browser interactions"},
    {"name": "firecrawl-build", "provider": "firecrawl", "category": "web", "description": "Web search, scraping, and extraction"},
    {"name": "browserbase", "provider": "browserbase", "category": "web", "description": "Browser automation at scale"},
    # Testing
    {"name": "playwright-skill", "provider": "testmu-ai", "category": "testing", "description": "Generate Playwright E2E tests"},
    {"name": "cypress-skill", "provider": "testmu-ai", "category": "testing", "description": "Generate Cypress E2E and component tests"},
    {"name": "jest-skill", "provider": "testmu-ai", "category": "testing", "description": "Generate Jest unit and integration tests"},
    {"name": "selenium-skill", "provider": "testmu-ai", "category": "testing", "description": "Generate Selenium WebDriver tests"},
    # Backend & infra
    {"name": "workers-best-practices", "provider": "cloudflare", "category": "devops", "description": "Review and author Cloudflare Workers code"},
    {"name": "netlify-functions", "provider": "netlify", "category": "devops", "description": "Build serverless API endpoints"},
    {"name": "next-best-practices", "provider": "vercel-labs", "category": "devops", "description": "Next.js best practices and patterns"},
    {"name": "terraform-style-guide", "provider": "hashicorp", "category": "devops", "description": "Generate Terraform HCL following conventions"},
    # Data & databases
    {"name": "clickhouse-best-practices", "provider": "clickhouse", "category": "data", "description": "Best practices for ClickHouse"},
    {"name": "azure-cosmos-ts", "provider": "microsoft", "category": "data", "description": "Cosmos DB NoSQL CRUD operations"},
    {"name": "postgres-best-practices", "provider": "supabase", "category": "data", "description": "PostgreSQL best practices for Supabase"},
    {"name": "duckdb", "provider": "duckdb", "category": "data", "description": "Query files, databases, and cloud storage"},
    # Security
    {"name": "semgrep-rule-creator", "provider": "trailofbits", "category": "security", "description": "Create and refine Semgrep detection rules"},
    {"name": "static-analysis", "provider": "trailofbits", "category": "security", "description": "Static analysis with CodeQL and Semgrep"},
    {"name": "security-best-practices", "provider": "openai", "category": "security", "description": "Review code for security vulnerabilities"},
    {"name": "sentry-workflow", "provider": "sentry", "category": "security", "description": "End-to-end issue fixing with Sentry context"},
    # AI & ML
    {"name": "hugging-face-model-trainer", "provider": "huggingface", "category": "ai", "description": "Train models with TRL and optimization"},
    {"name": "replicate", "provider": "replicate", "category": "ai", "description": "Discover, compare, and run AI models"},
    {"name": "fal-generate", "provider": "fal-ai-community", "category": "ai", "description": "Generate images and videos using models"},
    {"name": "imagegen", "provider": "openai", "category": "ai", "description": "Generate and edit images via OpenAI API"},
    # API & integration
    {"name": "stripe-best-practices", "provider": "stripe", "category": "integration", "description": "Best practices for Stripe integrations"},
    {"name": "composio", "provider": "composiohq", "category": "integration", "description": "Connect AI agents to 1000+ external apps"},
    {"name": "apollo-federation", "provider": "apollographql", "category": "integration", "description": "Write Apollo Federation supergraph schemas"},
    # Docs & knowledge
    {"name": "notion-research-documentation", "provider": "openai", "category": "documents", "description": "Synthesize findings into structured briefs"},
    {"name": "audit-context-building", "provider": "trailofbits", "category": "security", "description": "Deep architectural context via code analysis"},
]


def _load_all() -> list[dict]:
    items = list(_SEED)
    # User override/extension file
    try:
        from app.config import settings  # noqa
    except Exception:
        pass
    ov = Path("data/skills_directory.json")
    if ov.exists():
        try:
            extra = json.loads(ov.read_text(encoding="utf-8"))
            if isinstance(extra, list):
                items.extend(x for x in extra if isinstance(x, dict) and x.get("name"))
        except Exception:
            pass
    # Attach a discoverable link + a stable id
    for it in items:
        it.setdefault("url", f"{_SOURCE}#{it.get('provider','')}-{it['name']}")
        it["id"] = f"{it.get('provider','')}/{it['name']}"
    return items


def directory(category: str = "", query: str = "") -> dict:
    """Browse the skills directory. Optional category filter + text search."""
    items = _load_all()
    if category:
        items = [i for i in items if i.get("category") == category]
    if query:
        q = query.lower()
        items = [i for i in items
                 if q in i["name"].lower() or q in i.get("description", "").lower()
                 or q in i.get("provider", "").lower()]
    categories = sorted({i["category"] for i in _load_all()})
    return {
        "skills": items,
        "count": len(items),
        "total": len(_SEED),
        "categories": categories,
        "source": _SOURCE,
        "note": "Discovery directory — follow each link to install in your agent tool. "
                "Runnable keyless HTTP tools are in the Plugins catalogue.",
    }
