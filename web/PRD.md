# MyDataTalk Cloud — Product Requirements (v1 / MVP)

This is the spec for the hosted product that lives behind login at
mydatatalk.ai — distinct from the open-source local Streamlit app
(`app.py` at the repo root), which stays as the self-hosted option
described in the main [README](../README.md).

Register/login is already built (Auth.js + Prisma + Postgres, see
`auth.ts`, `app/login`, `app/register`). Everything in this doc is new
work layered on top of that.

## 1. One-liner

Connect your database and your own AWS Bedrock account, ask questions
about your data in plain English, and get back SQL, a chart, and a
plain-English answer — with a way to save the good ones and eventually
turn them into a shareable report.

## 2. Users

Mixed, deliberately not narrowed to one persona: executives who just
want the answer and a chart, and analysts who want to see (and trust)
the SQL before they believe it. This drives requirement #6 (the
simple/detailed toggle) more than anything else in this doc — it's the
mechanism that lets one interface serve both without compromising
either.

## 3. Scope: MVP vs. fast-follow

You selected three "core" capabilities during scoping. They're not
equal in build cost, so here's the phasing call (this is the "breadth"
decision you asked me to make):

| Capability | MVP (v1) | Fast-follow |
|---|---|---|
| Ask a question in natural language → SQL → answer + chart | ✅ Full | — |
| Conversational chat with history (follow-up questions in context) | ✅ Full — the existing `analyst.py` engine already supports this | — |
| Agent that autonomously decomposes one ask into multiple SQL queries/steps | — | ✅ v1.1 |
| Dashboard of **manually saved** insights (pin a result from chat) | ✅ Full | — |
| Dashboard that **auto-generates** insights without being asked | — | ✅ v1.1 |
| Report/narrative builder (compose saved insights into a shareable doc) | — | ✅ v1.2 |

Reasoning: single-turn (and multi-turn-with-context) NL→SQL→chart is
the actual differentiator and is already proven to work in the local
app — it's the fastest path to a usable product. Autonomous
multi-step planning and unprompted insight generation are both
meaningfully harder (they require an agent loop with its own
judgment calls about what's "interesting") and aren't needed to
validate the core loop. The report builder is the least essential of
the five screens and composes *on top of* saved insights, so it
can't be built before dashboard/saved-insights exists anyway.

If you want a different cut line, this table is the thing to edit.

## 4. Screens

All five screens you listed are in scope for the product's shape;
MVP vs. fast-follow (per §3) determines how much *functionality* each
one has on day one.

### 4.1 Data source connection / setup
- Add a database connection (Postgres, MySQL, Snowflake — reuse the
  connector logic already in `postgres_client.py` / `mysql_client.py`
  / `snowflake_client.py` / `db_base.py`, ported or wrapped per §8).
- Add AWS Bedrock credentials (access key/secret/region) and pick a
  model from the live list (reuse `model_discovery.py`'s "load
  available models" logic).
- List of the user's saved connections; edit/delete; a "test
  connection" action before saving.
- Credentials must be encrypted at rest — this is new (§7).

### 4.2 Main chat / query interface
- Text input, conversation thread, per-database chat history (matches
  existing local-app behavior: switching connections switches
  context).
- Each turn shows: the plain-English answer, an inline chart, and
  (per the trust toggle, §6) the SQL and result table.
- "Save to dashboard" action on any turn.

### 4.3 Results & visualization view
- Full-size view of a single result: bigger chart, chart-type switch
  (line/bar/scatter/pie — matches existing auto-chart logic),
  data table, export (CSV at minimum).
- Reached by clicking into a chat turn or a dashboard tile.

### 4.4 Dashboard / saved insights
- Grid of saved tiles (chart + plain-English summary + link back to
  the SQL/turn that produced it).
- MVP: user manually pins tiles from chat. Fast-follow: the system
  proactively suggests/generates tiles.

### 4.5 Report / narrative builder
- Fast-follow (§3). Compose a set of saved insights into an ordered,
  shareable narrative — likely markdown or PDF export. Not specified
  further here since it's post-MVP; revisit once the dashboard exists.

## 5. Primary user flow (MVP)

1. Register/log in (already built).
2. Connect a database + Bedrock credentials, pick a model.
3. Ask a question in chat.
4. See plain-English answer + chart (simple mode) or also SQL + table
   (detailed mode).
5. Optionally save the result to the dashboard.
6. Ask a follow-up question — context carries over.

## 6. Trust & transparency: the simple/detailed toggle

- A per-user, per-message-overridable toggle.
- **Simple**: plain-English answer + chart only.
- **Detailed**: adds the generated SQL (rendered like the local app's
  expandable SQL block — editable and re-runnable), the raw result
  table, and light execution metadata (which model answered, whether
  schema retrieval used the full schema or a vector-search subset).
- The SQL safety guard already built in `analyst.py`
  (`_ensure_readonly` — single-statement, SELECT/WITH only, no
  DML/DDL keywords) must protect the "edit & re-run" path here exactly
  like it does in the local app. Non-negotiable — this is what makes
  showing editable SQL to non-technical execs safe in the first place.

## 7. Non-functional requirements

- **Multi-tenant isolation**: one user's connections, credentials,
  chat history, and dashboard must never be visible to another user.
  Every query against the accounts DB must be scoped by the
  authenticated user's id.
- **Credential encryption**: DB passwords and AWS secret keys are
  encrypted at rest (e.g., app-level encryption before writing to
  Postgres, or a secrets manager), not stored in plaintext — this is
  a step up from the local app, which only ever holds credentials in
  memory for a single local user.
- **Read-only execution**: carried over from `analyst.py` as-is (see
  §6) — no new SQL execution path may bypass it.
- **Responsive web, desktop + mobile**: chat, charts, and tables need
  to degrade sensibly on a phone-width viewport (charts resize,
  tables scroll or collapse to a card view) — this wasn't a
  requirement for the local Streamlit app and is new work.
- **Bring-your-own AWS**: users supply their own Bedrock credentials
  and pay AWS directly, matching the local app's cost model — this
  product is not proxying/reselling model access.

## 8. Technical approach — open decision

The NL→SQL→execute→summarize pipeline already exists, is tested, and
has the read-only guard: `analyst.py`, `bedrock_client.py`,
`db_base.py` + the per-database connector modules, all in Python at
the repo root.

**Recommendation**: don't reimplement this in TypeScript. Wrap the
existing Python modules in a small internal service (e.g., FastAPI)
that the Next.js app's API routes call server-to-server. This keeps
the already-verified SQL generation and safety logic as the single
source of truth instead of maintaining two implementations that could
drift apart.

The alternative — porting the pipeline to TypeScript so everything
lives in one Next.js codebase — is simpler operationally (one
runtime, one deploy) but means re-verifying the read-only guard,
schema formatting, and Bedrock streaming logic from scratch in a new
language.

This needs your sign-off before implementation starts, since it
determines the whole backend shape (a second deployed service vs.
one). Flagging it here rather than deciding silently.

## 9. New data model (beyond the existing `User` table)

Sketch, not final schema — for scoping purposes:

- `Connection` — belongs to a user; db type, encrypted credentials,
  display name.
- `BedrockCredential` — belongs to a user; encrypted AWS keys, region,
  selected model.
- `Conversation` / `Message` — chat history, scoped to a user +
  connection (currently the local app only keeps this in memory per
  session; the cloud version needs to persist it).
- `DashboardTile` — a saved insight: references the message/query it
  came from, chart config, summary text.

## 10. Design direction (the "vibe" call)

Continue the existing MyDataTalk visual language from the marketing
site into the authenticated app rather than introducing a second
design system: the same blue-600/zinc palette, Geist font, minimal
Vercel-style density. Given the mixed exec/analyst audience, lean
toward "precise and calm" over playful — data-dense where it matters
(tables, SQL) but uncluttered everywhere else. Charts should read the
same as the local app's (Plotly, `template="plotly_white"`) for visual
consistency between the two products.

## 11. Explicitly out of scope for v1

- Autonomous multi-step agent planning (§3)
- Auto-generated dashboard insights (§3)
- Report/narrative builder (§3)
- Team/multi-user accounts sharing one connection (single-user
  accounts only for now — no org/workspace concept)
- Anything beyond CSV export (PDF export, scheduled email reports,
  etc.)
- Non-Bedrock model providers (OpenAI, Anthropic direct API, etc.) —
  Bedrock-only, matching the local app
