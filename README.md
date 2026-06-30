@"

\# Atlas



A personal AI browser platform that makes the internet a tool, not just a destination.



Search, build tools, generate media, run agents, and browse privately — all from one interface powered by local and cloud AI models.



\## What it does



\- \*\*AI search\*\* — semantic search over crawled pages + live web, with cited answers

\- \*\*Tool builder\*\* — land on any webpage, Atlas reads it and auto-generates a reusable tool with a UI panel

\- \*\*Media generation\*\* — image, video, and audio from a single command, routed to local GPU or cloud APIs

\- \*\*Agent layer\*\* — type a goal, Ruflo plans and executes it across multiple pages using parallel agents

\- \*\*Code IDE\*\* — Monaco editor with Claude Code AI completion, sandboxed runner, git integration

\- \*\*Anonymous browsing\*\* — Tor routing, fingerprint spoofing, no-log mode, local-only inference



\## Stack



| Layer | Tech |

|-------|------|

| Backend | FastAPI · Python |

| Frontend | React · Vite · Oxlint |

| Local models | Ollama (Llama 3.1 8B, Mistral 7B) · RTX 5070 |

| Free cloud models | NVIDIA NIM |

| Paid models | Claude API (Haiku / Sonnet) |

| Free Pro access | Claude Pro OAuth via Claude Code SDK |

| Agent layer | Ruflo (npx ruflo) |

| Browser engine | Playwright (headless Chromium) |

| Vector search | ChromaDB + nomic-embed-text |

| Media | FLUX local · DALL-E 3 · RunwayML · ElevenLabs |

| Privacy | Tor · playwright-extra stealth |



\## Project structure



&#x20;   atlas/

&#x20;   ├── backend/app/

&#x20;   │   ├── models/       # Phase 1 — model router

&#x20;   │   ├── browser/      # Phase 2 — Playwright engine

&#x20;   │   ├── search/       # Phase 3 — ChromaDB + memory

&#x20;   │   ├── media/        # Phase 4 — image/video/audio

&#x20;   │   ├── ide/          # Phase 5 — code sandbox

&#x20;   │   ├── privacy/      # Phase 6 — Tor + fingerprinting

&#x20;   │   ├── safety/       # Phase 7 — safe browsing

&#x20;   │   ├── toolbuilder/  # Phase 8 — auto tool gen ⭐

&#x20;   │   ├── agents/       # Phase 9 — Ruflo agents

&#x20;   │   └── api/          # FastAPI routes

&#x20;   ├── frontend/         # React + Vite UI

&#x20;   ├── notes/            # Dev decisions

&#x20;   └── data/             # Local data (gitignored)



\## Roadmap



| Phase | Focus | Target |

|-------|-------|--------|

| 0 | Setup ✅ | Jun 2026 |

| 1 | Model router | Jul 2026 |

| 2 | Browser engine | Jul 2026 |

| 3 | Search + memory | Aug 2026 |

| 4 | Media generation | Sep 2026 |

| 5 | Code IDE | Sep 2026 |

| 6 | Privacy layer | Oct 2026 |

| 7 | Safe browsing | Oct 2026 |

| 8 | Tool builder ⭐ | Nov 2026 |

| 9 | Agent layer | Dec 2026 |

| 10 | UI + search | Jan 2027 |

| 11 | Package + ship | Feb 2027 |



\## Status



Phase 0 complete. Starting Phase 1 (model router) next.



Private project — solo development.

"@ | Out-File -FilePath README.md -Encoding utf8

