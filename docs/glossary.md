# Glossary

Plain-language definitions of the core concepts in SafeAI, with a note on how
each applies to *this* project. Intended for any reader — including reviewers
who are not specialists in every area.

---

### Clean Architecture

A way of organizing code into concentric layers (domain → application →
interface/infrastructure) where **dependencies only point inward**. The inner
**domain** holds business rules in plain code and knows nothing about databases
or web frameworks; outer layers are replaceable "details."

*In SafeAI:* `domain/` (entities like `EmergencyEvent`) is framework-free;
`infrastructure/` (SQLAlchemy, scikit-learn) implements interfaces the domain
defines. This makes the core testable and the tech choices swappable. See
[architecture.md](architecture.md#2-clean-architecture).

---

### REST API

**Representational State Transfer** — an HTTP API style where **resources**
(users, contacts, events) are addressed by URLs and acted on with standard verbs
(`GET` read, `POST` create, etc.), returning JSON with meaningful status codes.

*In SafeAI:* the backend exposes a versioned REST API under `/api/v1` (e.g.
`POST /api/v1/emergency/sos`). See [api-contract.md](api-contract.md).

---

### JWT (JSON Web Token)

A compact, **signed** token that carries claims (like a user id) and can be
verified without a server-side session. The server signs it with a secret; the
client sends it back on each request to prove who it is. It is *signed, not
encrypted* — so it must not contain secrets, and it travels over HTTPS.

*In SafeAI:* login returns a JWT access token; protected endpoints require
`Authorization: Bearer <token>`. The signing secret comes from the environment,
never from source. See [architecture.md](architecture.md#7-security-architecture).

---

### Geospatial data

Data tied to a location on Earth — here, **latitude/longitude** coordinates.
Working with it efficiently (e.g. "events near this point") needs spatial types
and indexes rather than plain number comparisons.

*In SafeAI:* coordinates are stored on events, locations, and risk assessments;
PostgreSQL's **PostGIS** extension is the roadmap for fast spatial queries. See
[database-design.md](database-design.md#6-geospatial-roadmap-postgis).

---

### Machine Learning (ML)

Building a model that **learns patterns from data** to make predictions, instead
of hand-coding every rule. The model is *trained* on examples, then *serves*
predictions on new inputs.

*In SafeAI:* a scikit-learn model learns to estimate how risky a location/time
is from features (hour, history, context). See
[architecture.md](architecture.md#6-ai-risk-assessment-flow).

---

### Classification

A type of ML task where the model predicts a **category** (or the probability of
a category) rather than a continuous number. *Binary* classification chooses
between two classes (e.g. "elevated risk" vs "not").

*In SafeAI:* the risk model is a classifier; its predicted probability of the
"risky" class becomes the **risk score**.

---

### Risk score

A single number in **`[0, 1]`** representing the model's estimated probability of
elevated risk for a location/time. It is bucketed into bands for humans:
`low` (< 0.34), `moderate` (0.34–0.66), `high` (> 0.66).

*In SafeAI:* returned by `POST /risk/analyze` and stored with the `model_version`
that produced it, so results are reproducible and auditable.

---

### Real-time systems

Systems where **timeliness is part of correctness** — a response that is correct
but late is effectively wrong. They emphasize low, predictable latency and
durability of critical actions.

*In SafeAI:* SOS activation is the real-time-sensitive path. We make it fast and
**durable** by persisting the event *before* attempting notification, and we keep
the operational "any active emergencies?" query backed by a small index so it
stays fast as data grows. See [architecture.md](architecture.md#4-sos-workflow).

---

### Scalability

The ability of a system to **handle growth** (more users, data, requests) by
adding resources, without a redesign. *Horizontal* scaling adds more instances;
*vertical* scaling makes one instance bigger.

*In SafeAI:* the API is **stateless** (JWT), so it scales horizontally behind a
load balancer; the database scales via indexing, time-partitioning of location
history, and read replicas. We scale by moving boundaries that already exist
rather than rewriting. See [architecture.md](architecture.md#8-scalability-considerations).

---

### Idempotency

An operation is **idempotent** if performing it multiple times has the **same
effect as performing it once**. Crucial for actions a client might retry.

*In SafeAI:* a panicked user may tap SOS twice, or the network may retry. The
client sends an **`Idempotency-Key`**; the server creates the event only once for
that key and returns the same event on replay — so one emergency never becomes
several. See [api-contract.md](api-contract.md#emergency).

---

### Port / Adapter (bonus term used throughout)

A **port** is an interface the domain defines (e.g. `Notifier`, `RiskAssessor`);
an **adapter** is a concrete implementation in `infrastructure/` (e.g.
`LogNotifier`, `SklearnRiskAssessor`). Swapping an adapter (log → SMS, local →
remote model) doesn't change the domain. This is the mechanism behind SafeAI's
testability and swappability.

---

### Application factory

A function (`create_app`) that **constructs and configures** the application
(routes, settings, middleware) and returns it, instead of building it at import
time. It makes testing and multiple configurations clean.

*In SafeAI:* `create_app()` builds the FastAPI app; tests build their own
instance with test settings.
