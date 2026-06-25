# Security Design

> The deep-dive companion to [architecture.md §7](architecture.md#7-security-architecture).
> That section summarizes the controls; this document explains the **threat
> model**, **privacy posture**, and **reasoning** behind them.

## Why SafeAI is not a normal CRUD application

Most CRUD apps protect data because leakage is *embarrassing or costly*. SafeAI
protects data because leakage can be *physically dangerous*. The platform holds:

- a user's **real-time and historical location**,
- their **emergency-contact graph** (who matters to them, and how to reach them),
- the **fact that an SOS was triggered** — and when, and where.

For the population this product serves, a credible adversary is often **not** a
distant hacker but an **intimate-partner abuser or stalker** who already knows
the victim, may know their password, and may have intermittent physical access
to their phone. A bug that exposes "last known location" is, in this context, a
safety incident — not a privacy footnote.

This document therefore treats **confidentiality of location**, **integrity of
the SOS path**, and **availability of the emergency action** as life-safety
properties, and designs accordingly: *data minimization first, defense in depth,
and fail-safe behavior on the emergency path.*

---

## Security principles

Six principles govern every decision in this document:

1. **Privacy by default** — the safe setting is the default; users never have to
   opt in to having their data protected.
2. **Least privilege access** — every actor (and every request) gets only the
   access it needs; identity is derived from a verified token, never assumed.
3. **Minimum data collection** — collect and retain the least data the safety
   function requires; the safest data is data never stored.
4. **Secure handling of emergency information** — location, contacts, and the
   fact-of-an-SOS are treated as life-safety data, not ordinary records.
5. **Fail safely during critical events** — the SOS path persists the event
   before notifying and is idempotent, so a failure never loses or duplicates an
   emergency.
6. **Audit important security actions** — security-relevant actions (auth,
   destructive changes, notifications) are timestamped and, as features land,
   logged for accountability and incident reconstruction.

---

## 1. Assets and data classification

| Asset | Classification | Why it matters |
|-------|----------------|----------------|
| Password hash | Secret | Account takeover → full surveillance / SOS sabotage |
| Session/JWT | Secret | Bearer access to everything the user can do |
| Location (live + history) | **Critical / life-safety PII** | Direct physical-safety risk if leaked |
| Emergency contacts | Sensitive PII | Reveals the victim's support network; abuse vector |
| Emergency events (existence + status) | **Critical** | Reveals that/when a user felt unsafe |
| Risk assessments | Sensitive | Infers location patterns and vulnerability |
| Email / name | PII | Identity, account enumeration |
| JWT signing secret, DB credentials | Secret | Compromise breaks the whole trust model |

**Design consequence:** location and emergency-event data are the crown jewels.
Every control below is prioritized by its effect on those two assets.

---

## 2. Threat actors

| Actor | Capability | Primary goal |
|-------|-----------|--------------|
| **Intimate-partner abuser / stalker** | Knows victim; may know credentials; intermittent device access | Locate/track victim; disable or monitor SOS |
| External attacker (remote) | Network access, no prior knowledge | Mass data theft, account takeover, abuse of endpoints |
| Malicious/curious insider | Some system access | Snoop on specific users' locations |
| Honest-but-curious platform | Operates the system | Over-collection / over-retention of PII |
| Compelled disclosure (legal) | Lawful process | Bulk access to location history |

The first actor is what makes this product distinctive. Several controls below
exist specifically to limit what an attacker **who already has some access** can
learn or do — not just to keep strangers out.

---

## 3. Trust boundaries

```
   ┌────────────┐  HTTPS   ┌──────────────────────────┐   internal    ┌────────────┐
   │  Browser   │ ───────► │  FastAPI (app instances) │ ───────────►  │ PostgreSQL │
   │  (client)  │ ◄─────── │  authZ on every request  │ ◄───────────  │  (PII)     │
   └────────────┘          └────────────┬─────────────┘               └────────────┘
        ▲   untrusted                    │ in-process                        ▲
        │   (validate all input)         ▼                                   │ encrypted
        │                        ┌──────────────┐                     at rest (deploy)
   trust boundary 1        ML risk model (no PII egress)        trust boundary 3
                            trust boundary 2 (future: notifier → SMS/push provider)
```

- **TB1 — Client ↔ API:** everything from the client is untrusted; validate at
  the boundary, authenticate, and authorize per request.
- **TB2 — API ↔ external providers (future):** when SMS/push is added, a third
  party receives a phone number + minimal message. That egress is a deliberate,
  reviewed boundary (data-sharing agreement, least data).
- **TB3 — API ↔ database:** PII at rest; access only via parameterized queries;
  encryption at rest in production.

---

## 4. STRIDE analysis

| Threat | Example against SafeAI | Mitigation | Status |
|--------|------------------------|-----------|--------|
| **Spoofing** | Stealing a token to impersonate a user | Signed JWT (HS256, pinned algorithm); short expiry; HTTPS-only transport | Tokens ✅ / refresh rotation ⬜ |
| **Tampering** | Altering an SOS event or another user's data | Parameterized ORM writes; per-user authorization; domain-enforced status transitions | Validation ✅ / authZ ⬜ (Phase 2/3) |
| **Repudiation** | "I never triggered/none was sent" | `created_at`/`updated_at` on events; planned notification audit log | Timestamps ✅ / audit log ⬜ (Phase 3) |
| **Information disclosure** | Reading another user's location/history | Authorization on every read; data minimization; error hygiene (no leakage) | Error hygiene ✅ / authZ ⬜ |
| **Denial of service** | Flooding `/auth/login` or `/emergency/sos` | Rate limiting at edge + per-sensitive-endpoint; idempotency on SOS | ⬜ (Phase 6) / idempotency designed |
| **Elevation of privilege** | A user acting as another / as admin | No ambient authority; current user derived only from a verified token | Token model ✅ / dependency ⬜ (Phase 2) |

**Status legend:** ✅ implemented in Phase 1 · ⬜ designed, lands in the noted phase.
This table is deliberately honest about the Phase-1 gap: the *mechanisms* (token
verification, the envelope, validation) exist; the *per-resource authorization
checks* arrive with the features that own those resources.

---

## 5. Abuse cases (safety-specific)

These go beyond generic security bugs — they are ways the product itself could be
*turned against* the person it protects.

1. **Surveillance via account takeover.** If an abuser learns the password, they
   can read live location. → Strong hashing, login rate limiting, and (roadmap)
   refresh-token rotation + new-device/login notifications so takeover is
   noticed. Long term: optional 2FA.
2. **Silent SOS sabotage.** An attacker with the account could delete contacts or
   cancel events. → Status transitions are validated in the domain; destructive
   actions are auditable (`updated_at`, planned audit log); contacts deletion is
   logged.
3. **Contact / account enumeration.** Probing whether an email or phone exists. →
   Identical responses for login failures (`invalid_credentials`), generic
   messages, and rate limiting; never confirm existence on auth paths.
4. **SOS spam / notification abuse.** Repeated SOS to harass contacts or exhaust
   quota. → **Idempotency-Key** collapses retries into one event; rate limiting
   on the SOS endpoint; best-effort, deduplicated notification.
5. **Location inference from side channels.** Risk scores or timing could leak
   whereabouts. → Risk data is de-identified where possible (`ON DELETE SET NULL`
   on `risk_assessments.user_id`); responses avoid echoing precise internal state.
6. **Over-retention as a standing risk.** The safest data is data not kept. →
   Location-history retention/TTL (see §7).

---

## 6. Security controls in place (Phase 1)

| Control | Implementation | Location |
|---------|----------------|----------|
| Password hashing | bcrypt, per-hash salt, plaintext never stored/logged | `app/core/security.py` |
| Token integrity | JWT signed HS256, **algorithm pinned** on decode (no alg-confusion), expiry enforced | `app/core/security.py` |
| Secret management | Secrets from env via `pydantic-settings`; **production fails fast** on the placeholder JWT secret; `.env` git-ignored | `app/core/config.py`, `.gitignore` |
| Input validation | All inbound payloads validated by pydantic DTOs at the boundary; coordinate ranges enforced in the domain | `app/api/.../schemas`, `app/domain/value_objects/coordinates.py` |
| SQL injection prevention | SQLAlchemy parameterized queries / ORM only | `app/infrastructure/db` |
| Error hygiene | Global exception handlers return the safe envelope; internal detail logged server-side, never returned | `app/api/errors.py` |
| CORS | Explicit allow-list of origins (no wildcard with credentials) | `app/main.py` |
| Transport | HTTPS terminated at the proxy/LB in production | deployment |
| Idempotency (abuse-limiting) | Unique `idempotency_key` on emergency events (designed) | `docs/database-design.md` |

---

## 7. Privacy by design & data minimization

Privacy *is* security for this product. Principles applied:

- **Collect the minimum.** Only the fields needed for the safety function are
  stored (see [database-design.md](database-design.md)). No precise tracking
  beyond what features require.
- **Retain the minimum.** `location_history` is the highest-risk table; it is
  designed for **time-partitioning with a defined retention window** so old
  precise locations are dropped, not hoarded. (Enforcement lands with the table
  in Phase 4.)
- **Asymmetric deletion.** When a user is deleted, personal data **cascades**
  away (contacts, events, locations, recommendations), while `risk_assessments`
  uses `ON DELETE SET NULL` to keep de-identified model-quality data — privacy
  for the person, utility without the identity.
- **Encryption at rest** for the database in production (managed-Postgres
  feature); **in transit** via TLS everywhere.
- **No PII in logs.** Logging avoids secrets and PII by convention and review;
  location and tokens are never logged.
- **Least data on egress.** Future SMS/push sends only the minimum (a contact's
  number + a short message), never the full event record.

---

## 8. Authentication & authorization model

- **Authentication:** stateless JWT access tokens, signed with an
  env-provisioned secret, short-lived. The current user is derived **only** from
  a verified token — there is no ambient or implicit identity.
- **Authorization:** every resource (contacts, events, locations,
  recommendations) is owned by exactly one user; every read/write checks that the
  authenticated user **is the owner**. This per-request ownership check is the
  single most important defense against the information-disclosure threat, and is
  implemented as the feature endpoints land (Phase 2 onward).
- **Statelessness trade-off:** JWTs cannot be revoked server-side mid-lifetime.
  This is accepted for now with short expiry; **refresh-token rotation** and a
  revocation list are on the roadmap to support "log out everywhere" and to blunt
  the account-takeover abuse case.

---

## 9. Secure development lifecycle

- **Static gates in CI:** `ruff` (lint), `mypy --strict` (types), `pytest` with a
  coverage floor — every push. Type safety removes a class of injection/`None`
  bugs before runtime.
- **Tests as security tests:** failure-path and authorization tests are
  first-class (e.g. error responses must not leak internal detail — asserted in
  `tests/test_error_handlers.py`).
- **Planned additions:** `bandit` (Python SAST) and `pip-audit` / `npm audit`
  (dependency CVEs) in CI; **dependency pinning / lockfiles** for reproducible,
  auditable builds; secret-scanning on commit. These close the supply-chain and
  SAST gaps noted in review.
- **Least-privilege runtime:** the backend container runs as a **non-root** user.

---

## 10. Incident response posture

- **Containment:** rotate the JWT signing secret to invalidate all tokens; rotate
  DB credentials; both are env-provisioned, so rotation needs no code change.
- **Blast-radius limits:** per-user authorization means one compromised account
  does not expose others; stateless API instances can be cycled quickly.
- **Detectability:** structured logs (no PII), health/readiness signals, and the
  planned notification/audit log support reconstructing what happened.
- **Breach handling:** given the life-safety nature of location data, a breach
  affecting location/events is treated as **high-severity** with prompt user
  notification — not a routine disclosure.

---

## 11. Compliance alignment

SafeAI is built to be consistent with modern data-protection principles
(GDPR-style and India's DPDP Act — relevant given the user base):

- **Lawful, minimal processing** — collect only what the safety function needs.
- **Purpose limitation** — location is used for safety/risk, not profiling.
- **Storage limitation** — retention windows on the most sensitive data.
- **Right to erasure** — user deletion cascades personal data.
- **Integrity & confidentiality** — encryption in transit/at rest, access control.

These are design commitments; formal compliance work accompanies any real
deployment handling live user data.

---

## 12. Security roadmap (by phase)

| Phase | Security work |
|------:|---------------|
| 2 | JWT auth dependency; per-user authorization on profile; login enumeration-safe responses |
| 3 | Per-user authorization on contacts/events; SOS idempotency; notification audit log |
| 4 | Location-history retention/TTL + partitioning; tight authZ on location reads |
| 5 | De-identification of risk features; model-input validation |
| 6 | Rate limiting (login/SOS); security headers; `bandit`/`pip-audit` in CI; dependency pinning; refresh-token rotation; encryption-at-rest config |

---

## 13. Summary

SafeAI's security model starts from a harder premise than CRUD: the adversary may
be close to the user and may already hold some access, and the data at stake is
physical safety. The response is **data minimization first**, **authorization on
every access**, **fail-safe and idempotent emergency handling**, and **honest
phasing** — the mechanisms exist in Phase 1, and the per-resource controls land
with the features that own each resource. Nothing in this document claims a
control the code does not yet implement; the status columns make the line between
*built* and *planned* explicit.
