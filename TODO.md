# SSOT — Everest Capital Task Queue
# Single source of truth for all Claude Code sessions
# Updated: 2026-02-26 by Claude AI Architect

## 🔴 ACTIVE — BidDeed.AI × ZoneWise.AI (DiscoverWise Phase 2)

- [ ] **[BidDeed]** Run migration: `psql "$DATABASE_URL" -f sql/migrations/001_capability_registry.sql`
- [ ] **[BidDeed]** Implement `/api/v1/health` endpoint (query insights + multi_county_auctions)
- [ ] **[BidDeed]** Implement `/api/v1/auctions/county/{county}` (map overlay endpoint)
- [ ] **[BidDeed]** Implement `/api/v1/auctions` (paginated list with filters)
- [ ] **[BidDeed]** Implement `/api/v1/auctions/{case_number}` (HOA plaintiff flag logic)
- [ ] **[BidDeed]** Implement `/api/v1/auctions/{case_number}/report` (Supabase storage signed URL)
- [ ] **[BidDeed]** Implement `/api/v1/pipeline/trigger` (GitHub Actions dispatch)
- [ ] **[BidDeed]** Add BIDDEED_API_KEY to GitHub Secrets
- [ ] **[BidDeed]** Deploy render.yaml → confirm biddeed-api service live on Render
- [ ] **[ZoneWise]** Create `src/clients/biddeed_client.py` in zonewise-agents
- [ ] **[ZoneWise]** Create `src/agents/discoverwise_agent.py` LangGraph agent
- [ ] **[ZoneWise]** Verify sync-claude-skills.yml triggered after brevard-bidder-scraper push

## 🟡 QUEUED — ZoneWise Platform

- [ ] **[ZoneWise]** LienWise agent (AcclaimWeb integration via BidDeed API)
- [ ] **[ZoneWise]** CMAwise agent (BCPAO sales history comparable analysis)
- [ ] **[ZoneWise]** Map overlay UI — auction pins on Mapbox (BID=green, REVIEW=orange, SKIP=red)
- [ ] **[ZoneWise]** Property drawer — ZONING + AUCTION tabs
- [ ] **[ZoneWise]** NLP intent classifier for DiscoverWise chatbot queries
- [ ] **[ZoneWise]** Alert system (discoverwise_alerts table + email trigger)
- [ ] **[ZoneWise]** realauction.com scraper (67 counties tax deeds)

## 🟢 COMPLETED

- [x] .claude/ skills stack deployed to 8 repos (2026-02-26)
- [x] CoStar architecture decided: Option B (BidDeed external API)
- [x] Capability registry schema designed + seeded
- [x] BidDeed FastAPI skeleton (contracts defined)
- [x] sync-claude-skills.yml GitHub Action written
- [x] CraftAgents source configs (biddeed-api, supabase, github)
- [x] DiscoverWise PRD v1.0 complete
- [x] PROJECT_STATE.json updated with architecture decisions

---
## Protocol
Claude Code: always load this file at session start via /prime
Find first unchecked [ ] item in ACTIVE section → that is your task
Mark [x] and push when complete
