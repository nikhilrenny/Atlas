\# Atlas



A personal AI browser platform that makes the internet a tool, not just a destination.



Search, build tools, generate media, run agents, and browse privately — all from one interface powered by local and cloud AI models.



\## What it does



\- \*\*AI search\*\* — semantic search over crawled pages + live web, with cited answers

\- \*\*Tool builder\*\* — land on any webpage, Atlas auto-generates a reusable tool with a UI panel

\- \*\*Media generation\*\* — image, video, and audio routed to local GPU or cloud APIs

\- \*\*Agent layer\*\* — type a goal, Ruflo plans and executes it with parallel agents

\- \*\*Code IDE\*\* — Monaco editor with Claude Code AI completion and sandboxed runner

\- \*\*Anonymous browsing\*\* — Tor routing, fingerprint spoofing, no-log mode



\## Stack



| Layer | Tech |

|-------|------|

| Backend | FastAPI · Python |

| Frontend | React · Vite · Oxlint |

| Local models | Ollama · RTX 5070 8GB |

| Free cloud | NVIDIA NIM |

| Paid models | Claude API (Haiku / Sonnet) |

| Free Pro | Claude Pro OAuth via Claude Code SDK |

| Agents | Ruflo (npx ruflo) |

| Browser | Playwright headless Chromium |

| Search | ChromaDB + nomic-embed-text |

| Media | FLUX · DALL-E 3 · RunwayML · ElevenLabs |

| Privacy | Tor · playwright-extra stealth |



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

| 9 | Ruflo agents | Dec 2026 |

| 10 | UI + search | Jan 2027 |

| 11 | Package + ship | Feb 2027 |



\---



Phase 0 complete. Private project — solo development.

