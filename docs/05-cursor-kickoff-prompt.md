# 05 — Cursor Kickoff Prompt

> Paste the block below as your first message to Cursor (agent mode) after unzipping the bundle into the repo root. Re-paste the "Per-phase protocol" section at the start of each new session if context gets long.

---

You are implementing **ScreenLoupe**, a Windows screen-magnifier tray app (Python 3.11 + PyQt6). This repo is a complete design-first handover: every behavior, API call, and tradeoff is already specified. Your job is faithful implementation, not redesign.

## Step 1 — Orient (do this before writing any code)

Read, in this exact order, and then give me a ~10-line summary proving you understood:
1. `KARPATHY.md` — your behavioral contract (binding)
2. `ARCHITECTURE.md` — module map, state machine, decisions D1–D8
3. `docs/01-product-spec.md` — exact behaviors, settings table, edge cases E1–E9
4. `docs/02-technical-design.md` — the Win32 mechanics (capture exclusion, click-through, DPI, hotkeys)
5. `docs/03-ui-ux-design.md` — visual design tokens and layouts
6. `docs/04-implementation-plan.md` — your execution roadmap
7. `CLAUDE.md` § Gotchas — nine mistakes you must not rediscover

Your summary must include: the three hardest technical problems and their solutions, the app's state machine states, and which coordinate space all core geometry uses.

## Step 2 — Execute phase by phase (docs/04 is the roadmap)

Per-phase protocol:
1. **Announce the phase** and restate its verify criteria from docs/04.
2. **State a short plan** (steps + verify per step) before coding.
3. **Implement** following `.cursorrules` and the directory layout in `CLAUDE.md` exactly. `pyproject.toml`, `installer/screenloupe.iss`, and `scripts/build.ps1` already exist — use them, don't regenerate them.
4. **Stop at the phase gate**: run what's runnable (pytest, ruff), then hand me the manual verify checklist for anything needing a live Windows display (overlays, hotkeys). Do NOT start the next phase until I confirm the gate passed.

Hard rules:
- **Phase 1 spikes come first and are non-negotiable.** If Spike A (capture exclusion) fails on my machine, STOP and tell me — the architecture needs rethink, and any further code would be wasted.
- One overlay state at a time; only `app.py` manages lifecycle/state.
- All core geometry in physical pixels; conversion only in `platformwin/dpi.py`.
- DPI awareness call is the first statement of `main()`, before QApplication.
- Never touch Qt objects from `keyboard`-hook callbacks — queued signals only.
- If anything in the docs seems wrong, contradictory, or you see a simpler approach: **say so and ask before deviating.** Cite the doc + section you're questioning. Never silently diverge.
- The four open questions in `docs/01 § 10` have chosen defaults — implement the defaults; don't re-ask unless implementation reveals a problem.

## Step 3 — Begin

Start now with the Step 1 reading + summary, then Phase 0 (scaffold). My environment: Windows 11, Python 3.11, repo root is this folder.

---

## Why this prompt is shaped this way (for the human, not for Cursor)

- **Forced reading order + comprehension proof**: agents skim. Demanding a summary with three specific facts makes skipping the docs detectable immediately.
- **Phase gates with human confirmation**: overlays and global hotkeys can't be verified headlessly. The gate prevents the classic agent failure of sprinting through six phases on top of a broken Phase 1.
- **"Spikes first, stop on failure"**: encodes the single most expensive possible mistake (building the product on a machine where capture exclusion misbehaves) as an explicit halt condition.
- **"Ask before deviating, cite the section"**: channels the agent's creativity into flagged proposals instead of silent drift — Karpathy Rule 1 made operational.
