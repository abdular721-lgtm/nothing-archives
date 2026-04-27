# Second Brain Upgrade — Plan & Record

Living document tracking the upgrade from voice assistant to a persistent, memory-augmented "second brain — actually a better brain."

Last updated: 2026-04-27.

---

## Goal (user's words)

> I want it to be my second brain actually a better brain.

Persistent semantic memory, long conversations across time, proactive task execution, pattern detection, decision support.

---

## Conversation summary (2026-04-27)

### User context
- ED doctor in Grimsby; app developer on the side.
- Primary device: Nothing Phone 2a (rooted, Magisk, Termux, Android 14, Nothing OS 2.5+).
- Working from OnePlus mobile during this conversation; Windows desktop dev machine exists but isn't always on.
- Has 4 websites already hosted on Hostinger.
- Already built ~38 voice scripts and a Claude Haiku 4.5 integration with 22 tools (`voice-claude`). Foundations are solid — this upgrade is incremental on top of them.

### Why we needed a new dev environment
- Tested raw Termux install of Claude Code v2: `npm install` succeeded but the postinstall failed with `Unsupported platform: android arm64`. Claude Code v2 has no bionic-libc target. **Raw Termux is dead for now.**
- Options compared:
  1. **Real chroot Ubuntu on phone** — viable on rooted device, but adds on-device complexity and shares phone resources.
  2. **Linux laptop + SSH** — cleanest, but laptop isn't always on.
  3. **proot Ubuntu + Termux bridge** — works but engineering overhead.
  4. **VPS + Tailscale** — chosen.

### Decision: VPS + Tailscale
- Always-on, decoupled from phone, accessible from any device (OnePlus, laptop, Nothing Phone).
- Side benefits: cron, off-site backups, n8n/Home Assistant relay, hosting for future side projects, optional consolidation of the 4 Hostinger sites later.
- Phone stays lean — does what it's good at (always-on voice frontend).

### VPS purchase decision
- **Provider:** Hostinger (existing ecosystem, single dashboard with the 4 websites).
- **Plan:** KVM 2 (2 vCPU, 8 GB RAM, 100 GB NVMe). Headroom for vector DB growth.
- **OS:** Ubuntu 24.04 LTS, plain (no control panel).
- **Location:** London (preferred, closest to Grimsby) or Frankfurt as fallback.
- **Billing:** monthly to start; switch to longer term after ~30 days of validation.
- **Hostname:** `brain` (or similar).
- **Add-ons:** decline all.

User is buying it in the morning.

---

## Architecture (target)

```
[Phone — Nothing Phone 2a]
   - voice frontend (wake word, STT, TTS)
   - voice-* scripts (action layer)
   - capture endpoints (share-sheet, mic)
   - voice-claude (orchestrator)
        │
        │  Tailscale tunnel
        ▼
[VPS — Hostinger KVM 2, Ubuntu 24.04]
   - Claude Code (dev environment)
   - Vector DB (Qdrant or SQLite + sqlite-vss)
   - Embedding pipeline
   - Nightly summarisation daemon (cron)
   - Pattern-detection cron
   - Capture endpoints (email-in, browser-extension API)
   - Off-site backups of phone state
        │
        ▼
[Claude API — Haiku 4.5 default, Sonnet for synthesis]
```

---

## Roadmap

### Phase 0 — Foundations (next session)
1. **Buy VPS** (user, in the morning).
2. **First-login hardening** — non-root user, key-only SSH, UFW firewall, fail2ban. ~15 min.
3. **Tailscale** — install on VPS and on Nothing Phone (Termux package). Verify VPS → phone SSH over the tunnel. ~10 min.
4. **Dev environment** — Node, npm, git, Claude Code, repo clone. ~10 min.
5. Sanity check: Claude Code on VPS can edit a file in the repo and SSH into the phone to test it.

### Phase 1 — Persistent memory (~3 sessions)
- Vector DB (Qdrant or SQLite + sqlite-vss) on VPS.
- Embedding pipeline (Voyage or OpenAI embeddings; fallback to local sentence-transformers).
- Memory schema:
  - `facts` — stable info about the user (preferences, recurring contexts).
  - `conversations` — voice-claude turns, chunked + embedded.
  - `journal` — voice journal entries, chunked + embedded.
  - `notes` — saved notes from `voice-note`.
  - `events` — calendar, reminders, completed tasks.
- Retrieval-augmented `voice-claude` — every query pulls top-k relevant memories, injects into Claude's context.
- Nightly summarisation daemon — compresses each day into themes, extracts entities, updates user profile.
- Schema versioning + atomic writes from day one.
- Migration path from existing `~/.voice-claude-history.json` (10-min TTL) → persistent store.

### Phase 2 — Capture surface (~2–3 sessions)
- Browser extension (clip articles, papers, highlights).
- Phone share-sheet endpoint (Android intent → POST to brain).
- Email-in capture (forward to a VPS-hosted address; parsed and added to memory).
- Optional: Kindle highlight sync.
- Optional: clinical reflections capture (with explicit privacy boundaries — see deferred decisions).

### Phase 3 — Proactive intelligence (~3–4 sessions)
- Pattern-detection daemon (sleep, mood, project mentions, abandoned ideas).
- Daily / weekly / monthly digests via the morning briefing.
- Decision-support contexts — when user asks "should I X?", retrieve all relevant past Y and surface them.
- Trust feedback loop — rate surfaced memories useful/not useful; tune retrieval.
- Voice tone for nudges — calm, direct (TBD with user).

### Phase 4+ — Beyond
- Anniversary / reminder surfacing.
- Cross-domain reasoning queries.
- Optional migration of Hostinger websites onto the VPS.
- Optional self-hosting of n8n / Home Assistant relay.

---

## Things the user is thinking about (captured)

- Wants it to be a *better* brain, not just a second one — implies proactive intelligence, not just storage.
- Open to spending on tools that earn their keep; £4/mo VPS is acceptable.
- Privacy-aware but hasn't formalised boundaries yet.
- Doesn't want abandoned scaffolding — wants the upgrade to actually be used daily.
- Comfortable with on-phone runtime + off-phone dev split.

---

## Tradeoffs accepted

- API cost: ~£5–15/mo (Haiku default, Sonnet for synthesis only). Manageable.
- Latency: 2–5s for chat, slightly more for retrieval-augmented queries.
- Persistent record of personal data on VPS — needs encryption at rest and explicit privacy choices (deferred).
- Behavioural change required: 70% of second-brain success is consistent capture; tech is the other 30%.
- Trust takes 2–3 months to build; first 4 weeks the brain feels sparse. Push through.

---

## Deferred decisions (revisit before/during Phase 1)

1. **Privacy boundaries** — what stays phone-only vs. syncs to VPS. Particularly important for any clinical reflections. Default: nothing clinical syncs unless explicitly tagged.
2. **Encryption at rest on VPS** — LUKS-on-LVM, or app-level encryption of memory store, or both? Key management?
3. **Backup strategy** — nightly snapshot of vector DB, journal, reminders. Where to? (Hostinger storage? S3-compatible? Phone-side rsync?)
4. **API budget cap** — set monthly spend alert; auto-fallback to Haiku-only if Sonnet usage spikes.
5. **VPS-unreachable failure mode** — confirm `voice-claude` degrades gracefully to keyword router (already does, needs verification under new architecture).
6. **Capture priority** — browser extension first, share-sheet first, or parallel?
7. **Proactive-nudge tone** — calm, direct, friendly? Affects system prompt.
8. **Quiet hours for proactive nudges** — stricter than current voice quiet hours?
9. **Trust period framing** — commit to a 2-week daily-use trial after Phase 1 ships before expanding scope.

---

## Constraints to remember (from CLAUDE.md and this conversation)

- `su shell -c` (uid 2000) for `am`/`cmd`/`pm`/`settings`/`svc`. `su -c` (uid 0) for kernel-level only.
- TTS over SSH causes OOM on sshd → always use `run-voice` for testing.
- `termux-microphone-record -e wav` lies; ffmpeg conversion mandatory.
- `sed -i` multi-line on Termux collapses to one line; use Python for multi-line edits.
- `set -e` in long-running daemons → kills daemon on any non-zero sub-command. Never use in daemons.
- Magisk root must use `su shell -c` for Android service calls.
- Tailscale package available in Termux.
- Claude Code v2 has no bionic-libc target → must run in glibc env (VPS).

---

## What I understood about the user (Claude's read)

- Builder-tinkerer who finishes things — 38 scripts and active commits prove it.
- Pragmatic about tradeoffs; wants honest answers, not over-promising.
- Cost-conscious but values utility framings.
- Decision-fatigued from clinical work; wants a tool that reduces friction, not adds it.
- Wants the assistant to fit into existing life patterns (commute, post-shift, on-the-move) rather than demand new ones.
- Privacy-aware in instinct, not yet in policy.
- Treats this conversation as planning, not vibing — wants concrete plans saved so we don't lose context.

---

## Next session checklist

When user returns with VPS bought:

- [ ] Get IP and confirm SSH access from any device.
- [ ] Walk through first-login hardening.
- [ ] Install Tailscale on VPS and Nothing Phone; verify mesh.
- [ ] Install Claude Code on VPS; confirm `claude --version`.
- [ ] Clone repo on VPS.
- [ ] Confirm VPS → phone SSH works over Tailscale.
- [ ] Begin Phase 1: persistent memory design (schema review with user before any code).
