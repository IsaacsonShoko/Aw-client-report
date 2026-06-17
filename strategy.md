# AW Client Report Portal: Strategy and Build Specification

**Assessment:** AI Engineer take home
**Source:** AW Client Report Portal PRD v1.0 (2026-04-09)
**Author:** Isaacson Shoko, 4D Analytics
**Purpose:** A complete strategy, data model, stack, and application structure that fully addresses the PRD, written to be verified against the original requirements.

---

## 1. Goal in one paragraph

EF is a three person financial planning firm in Atlanta serving roughly six wealthy families on quarterly retainers. Preparing the two client reports (SACS and TCC) currently takes a full working day per client because the team manually pulls balances from several sources and assembles the reports by hand in Canva and Word, introducing arithmetic errors. This build delivers a web portal where the team stores each client's fixed information once, enters the current quarter's balances into a structured form that does all the math automatically, and generates polished, layout stable PDF versions of both reports in minutes. The target is to cut preparation from a day to under an hour and to eliminate manual math errors.

---

## 2. Strategic approach and key judgment calls

These are the decisions that determine whether the build reads as senior or junior. They are stated up front because they shape everything below.

**No AI in version one, by design.** Although this is an AI Engineer assessment, the PRD states in three separate places that version one needs no AI. The work is structured data entry, deterministic arithmetic, and PDF generation. The correct demonstration of AI judgment here is restraint: build the right deterministic tool, then identify precisely where AI would add real value in a later version (for example, extracting balances from the bank's secure emails, or reconciling unreliable RightCapital data) without forcing it into scope now. Over engineering an LLM into pure arithmetic would fail the judgment this assessment is screening for.

**Fixed layout PDFs are the real engineering.** The math is trivial; the difficulty is producing PDFs that exactly match the firm's existing visual templates and never shift or misalign regardless of number size or how many accounts a client has. The planner stated this requirement three different ways. This pushes the implementation toward a fixed page layout with locked positioning, achieved by rendering HTML and CSS to PDF at a fixed page size rather than letting content flow freely. See section 10.

**Operate with incomplete inputs and document every assumption.** The PRD repeatedly references supporting documents (the Data Point List, sample PDFs, screenshots) that cannot be requested in an assessment. This is treated as part of the test. Where information is missing it is reconstructed from the acceptance criteria, the definitions table, and the screenshot descriptions, and every inference is recorded in section 4. The missing pixel exact templates are matched structurally, with a note that final pixel matching would be a short iteration once the real samples are available.

**Correctness first.** All monetary values are stored and computed as integer cents to avoid floating point rounding drift. All calculation logic lives in one isolated, unit tested module so the exact business rules can be proven correct independently of the database and the PDF layer. Nothing that can be derived is ever stored.

---

## 3. Assumptions

Recorded because the source documents cannot be requested. Each is a defensible reading of the PRD.

1. **Money is stored as integer cents.** Avoids floating point error in a tool whose entire purpose is accurate numbers.
2. **Derived values are never persisted.** Age, monthly excess, all section totals, the grand total, and the reserve target are computed on read, so they cannot drift out of agreement.
3. **Report history is preserved by snapshot.** Each generated report stores a snapshot of the salary, expense budget, and insurance deductibles in force at generation time, so re-downloading a past quarter reproduces the original numbers even after the profile changes.
4. **The reserve target is calculated, with an optional manual override.** The PRD calls it both static profile data and a calculated value. It is computed as six times monthly expenses plus total insurance deductibles, with a nullable override field for the rare case the team sets it manually.
5. **The $1,000 floor is a global constant** held in application config, not a per client field, since the PRD states it never changes.
6. **The trust is a separate entity, not an account,** so its exclusion from the non-retirement total is structural rather than a rule that must be remembered in code.
7. **Authoritative calculation is server side.** The data entry form shows live totals in the browser for usability, but the numbers placed in the PDF are always recomputed server side by the same calculation module.
8. **Canva export is treated as optional.** The PRD flags it as a nice to have and notes the planner would prefer the portal itself. PDF download is built as the core path; Canva export is scaffolded behind a feature flag.
9. **Final PDF layout is matched structurally, not pixel for pixel,** because the original sample PDFs are not available in the assessment. Colors, grouping, and field placement follow every described cue.

---

## 4. User stories

Refined from the PRD's four stories, with acceptance criteria preserved.

### US1: Client profile management
Store each client's fixed information once, replacing scattered spreadsheets and folders.

- Add a client with one or two persons (single or married), each with name, date of birth, auto calculated age, and last four of SSN.
- Define the account structure: retirement accounts (IRA, Roth IRA, 401K, pension) per spouse, non-retirement accounts (brokerage, joint), trust (property address), and liabilities (mortgage, auto loan, with interest rates).
- Enter static financial data: monthly salary after tax, agreed monthly expense budget, insurance deductibles total, optional reserve target override.
- Edit a client when things change (raise, new job, new or closed account).
- Client list view showing all clients with their last report date.

### US2: Quarterly data entry and automatic calculation
One click from a profile produces a structured form, pre-filled with static data and blank for the quarter's balances, with all math automatic.

- One click "Generate Report" creates a draft report for the client.
- Form is organized by report section, with static fields pre-filled and clearly labelled dynamic fields (for example "Roth IRA Balance", "Zillow Home Value").
- Each dynamic field shows the previous quarter's value as reference, with a "use last value" option.
- Incomplete required fields are highlighted; a report cannot be generated until all required fields are filled.
- All totals update live as balances are entered. Manual override is allowed on any field.

### US3: PDF generation
Generate both reports as layout stable PDFs matching the existing visual format.

**SACS (Simple Automated Cash Flow):** green Inflow bubble, red Outflow bubble with an X on the outflow arrow, blue Private Reserve section, connecting arrows, client name and date in the header, blue branding. Page one is the cashflow diagram (Inflow into Outflow into excess into Private Reserve). Page two shows the Private Reserve balance, the investment account balance, and the target savings number. Nothing on the page may move.

**TCC (Total Client Chart):** retirement accounts at the top split by spouse, non-retirement at the bottom, trust in the center, liabilities in a separate section. Green client info bubbles (names, ages, DOB, last four SSN). Account bubbles show type, last four of the account number, balance, and cash balance for investment accounts. Gray summary boxes for the two retirement totals, the non-retirement total, and the grand total. Liabilities show type, interest rate, and balance. The layout must handle one to six retirement accounts per spouse, one to six non-retirement accounts, and zero to three liabilities.

### US4: Export
- Download both SACS and TCC as separate, print ready PDFs from one interface.
- Optional "Export to Canva" for last minute visual edits, behind a feature flag.
- Report history: re-download any previous quarter's reports.

---

## 5. Data model

All money is integer cents. Dates are ISO 8601 text. Booleans are integers (0 or 1). Derived values are not stored.

```sql
-- The household. Holds fixed financial profile data.
CREATE TABLE clients (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    household_name              TEXT,
    marital_status             TEXT NOT NULL CHECK (marital_status IN ('single','married')),
    monthly_salary_cents        INTEGER NOT NULL,           -- SACS Inflow
    monthly_expense_budget_cents INTEGER NOT NULL,          -- SACS Outflow
    insurance_deductibles_cents  INTEGER NOT NULL DEFAULT 0,-- feeds reserve target
    reserve_target_override_cents INTEGER,                  -- nullable manual override
    created_at                  TEXT NOT NULL,
    updated_at                  TEXT NOT NULL
);

-- One row for single clients, two for married (Client 1 / Client 2).
CREATE TABLE persons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    person_role     TEXT NOT NULL CHECK (person_role IN ('client_1','client_2')),
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    date_of_birth   TEXT NOT NULL,        -- age computed from this, never stored
    ssn_last_four   TEXT NOT NULL,        -- text preserves leading zeros
    UNIQUE (client_id, person_role)
);

-- Static structure of savings and investment accounts. Balances are NOT here.
CREATE TABLE accounts (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id                INTEGER NOT NULL REFERENCES clients(id),
    person_id                INTEGER REFERENCES persons(id), -- null = joint / household
    category                 TEXT NOT NULL CHECK (category IN ('retirement','non_retirement')),
    account_type             TEXT NOT NULL,  -- IRA, Roth IRA, 401K, pension, brokerage, joint
    account_number_last_four TEXT,
    institution              TEXT,           -- e.g. Schwab
    is_investment_account    INTEGER NOT NULL DEFAULT 0, -- 1 = carries a cash balance
    display_order            INTEGER NOT NULL DEFAULT 0,
    active                   INTEGER NOT NULL DEFAULT 1
);

-- Zero or one per client. Holds the residence. Value is dynamic, on the report.
CREATE TABLE trusts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id        INTEGER NOT NULL UNIQUE REFERENCES clients(id),
    property_address TEXT NOT NULL
);

-- Static structure of debts. Balances are dynamic, on the report.
CREATE TABLE liabilities (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      INTEGER NOT NULL REFERENCES clients(id),
    liability_type TEXT NOT NULL,   -- mortgage, auto_loan, other
    description    TEXT,
    interest_rate  REAL,            -- shown on the TCC
    display_order  INTEGER NOT NULL DEFAULT 0,
    active         INTEGER NOT NULL DEFAULT 1
);

-- One quarterly report instance per client. Holds dynamic scalars and history snapshots.
CREATE TABLE reports (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id                     INTEGER NOT NULL REFERENCES clients(id),
    report_date                   TEXT NOT NULL,        -- header date
    report_period                 TEXT,                 -- e.g. 'Q2 2026'
    status                        TEXT NOT NULL DEFAULT 'draft'
                                  CHECK (status IN ('draft','complete')),
    private_reserve_balance_cents INTEGER,              -- dynamic this quarter
    trust_home_value_cents        INTEGER,              -- Zillow value this quarter
    snap_monthly_salary_cents     INTEGER NOT NULL,     -- snapshot for history fidelity
    snap_monthly_expense_budget_cents INTEGER NOT NULL,
    snap_insurance_deductibles_cents  INTEGER NOT NULL DEFAULT 0,
    created_at                    TEXT NOT NULL,
    updated_at                    TEXT NOT NULL
);

-- Dynamic account balances, one row per account per report.
CREATE TABLE report_account_balances (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id         INTEGER NOT NULL REFERENCES reports(id),
    account_id        INTEGER NOT NULL REFERENCES accounts(id),
    balance_cents     INTEGER NOT NULL,
    cash_balance_cents INTEGER,    -- only for investment accounts
    UNIQUE (report_id, account_id)
);

-- Dynamic liability balances, one row per liability per report.
CREATE TABLE report_liability_balances (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id              INTEGER NOT NULL REFERENCES reports(id),
    liability_id           INTEGER NOT NULL REFERENCES liabilities(id),
    balance_cents          INTEGER NOT NULL,
    interest_rate_snapshot REAL,
    UNIQUE (report_id, liability_id)
);
```

The client list's "last report date" is derived as the most recent `report_date` for each client, so it needs no column. The $1,000 floor is application config.

---

## 6. Calculation rules

The exact business logic, lifted from the PRD and treated as the authoritative specification for the calculation module. These are the rules a reviewer will check most closely.

| Output | Rule |
|---|---|
| Age | Computed from date of birth at render time |
| SACS monthly excess | Inflow minus Outflow |
| SACS reserve target | (6 times monthly expenses) plus total insurance deductibles |
| Client 1 retirement total | Sum of Client 1's retirement account balances |
| Client 2 retirement total | Sum of Client 2's retirement account balances |
| Non-retirement total | Sum of non-retirement account balances, trust excluded |
| Grand total net worth | Client 1 retirement plus Client 2 retirement plus non-retirement plus trust |
| Liabilities total | Sum of liability balances, shown separately, never subtracted from net worth |

Two rules are easy to get subtly wrong and are called out explicitly in the PRD: liabilities are never subtracted from net worth, and the trust is never folded into the non-retirement total. Both are enforced structurally by the data model and verified by unit tests.

---

## 7. Technology stack

Following the PRD's recommendations, with rationale and the one deliberate framework choice.

| Layer | Tool | Rationale |
|---|---|---|
| Hosting | Railway | PRD default; a small web app with no heavy compute |
| Web framework | Python with Flask | Lightweight, matches the Python backend recommendation, minimal overhead for a three user tool |
| Frontend | Server rendered HTML, CSS, vanilla JS | PRD preference; clean and simple, no framework overhead for three users |
| Database | SQLite on a Railway volume | PRD default; six clients is minimal volume |
| PDF generation | WeasyPrint | Renders the report HTML and CSS to vector PDF server side, so the same template drives the on screen preview and the downloaded file; layout is locked with a fixed `@page` size and absolute or grid positioning, which satisfies the no shifting requirement while being far faster to author than coordinate math. ReportLab is the fallback only if extreme programmatic control is ever needed |
| Optional export | Canva API behind a feature flag | Nice to have per the PRD |

Environment variables: `CANVA_API_KEY` (only if Canva export is enabled), `RAILWAY_DATABASE_PATH`.

No external API integrations in version one. All financial data is entered manually, which is intentional given RightCapital's unreliability, Schwab's credential sharing restrictions, and Pinnacle's email based balances.

---

## 8. Frontend design system

The portal is an internal tool for three staff at a firm serving high net worth families, so the visual direction is calm, precise, and quietly premium rather than expressive. Boldness is spent in one place only and everything else stays disciplined. Color is governed by the 60/30/10 rule and defined here as a fixed token set, so the build is consistent from the first screen rather than decided page by page.

### The 60/30/10 rule

Roughly sixty percent of any screen is the neutral base, thirty percent is the brand color that carries structure, and ten percent is a single accent reserved for the one thing the eye should land on. Each band has a job; none of it is decoration.

**60 percent, neutral base.** The quiet surfaces: page background, card fills, and whitespace. This is most of every screen and keeps a dense financial tool readable.
- `--bg` app background: `#F5F6F8`
- `--surface` cards and panels: `#FFFFFF`
- `--text` primary text: `#161A1D`
- `--muted` secondary text and hairline borders: `#6B7280` and `#E3E6EA`

**30 percent, brand blue.** The structural color the PRD already names as the firm's brand. Used for the top navigation, section headings, table header rows, and primary button fills.
- `--brand` deep professional blue: `#173A5E`
- `--brand-tint` links and hover states: `#2E6195`

**10 percent, accent.** A single warm gold reserved for the primary action on a screen (Generate Report, Download PDF), the active navigation state, and the one figure worth emphasizing. Kept scarce so it keeps its meaning.
- `--accent` gold: `#C39A3E`

Functional status colors (validation success, error, and the incomplete field highlight required by US2) sit outside the 60/30/10 budget, because they are momentary signals rather than part of the visual identity. Keep them muted and consistent across the app.

### Portal colors and report colors are two separate systems

This distinction is easy to get wrong and worth stating plainly. The 60/30/10 palette above governs the portal interface only. The SACS and TCC PDFs follow their own fixed semantic palette set by the firm's existing templates: green for Inflow, red for Outflow, blue for the Private Reserve, green client information bubbles, and gray summary boxes on the TCC. Those report colors carry data meaning, not interface styling, and must not be bent to match the portal chrome. The portal's brand blue and the report's Private Reserve blue may share a value, but the report greens and reds are semantic and never appear as interface accents. Exact report hex values follow the real sample PDFs once available, per assumption 9.

### Application notes

Define the tokens once as CSS custom properties on `:root` and derive every color from them, so the split is enforced rather than re-decided per screen. Hold the quality floor the design approach expects: responsive down to mobile, a visible keyboard focus state on every control, and reduced motion respected. Copy follows the same restraint, with each control naming the action that happens (Generate Report, Download PDF) and keeping that name through the whole flow.

---

## 9. Application structure

```
aw-report-portal/
├── app.py                  # Flask app factory and route registration
├── config.py               # constants incl. $1,000 floor, env var loading
├── db.py                   # SQLite connection, schema init, query helpers
├── schema.sql              # the DDL from section 5
├── seed.py                 # sample clients built from PRD example figures
├── calculations.py         # ISOLATED deterministic math, fully unit tested
├── repository.py           # data access: clients, accounts, reports, balances
├── routes/
│   ├── clients.py          # profile CRUD, client list
│   ├── reports.py          # generate, data entry, totals, status
│   └── exports.py          # PDF download, optional Canva export
├── pdf/
│   └── render.py           # WeasyPrint: render a report HTML template to vector PDF
├── templates/
│   ├── client_list.html
│   ├── client_form.html
│   ├── report_entry.html   # data entry, live totals via JS preview
│   ├── report_history.html
│   └── reports/
│       ├── sacs.html       # SACS report markup, shared by preview and PDF
│       └── tcc.html        # TCC report markup, variable bubbles via CSS grid
├── static/
│   ├── style.css           # portal chrome, 60/30/10 tokens from section 8
│   ├── report.css          # report layout, fixed @page size, locked positioning
│   └── entry.js            # live calculation preview only
├── tests/
│   └── test_calculations.py # proves every rule in section 6
├── requirements.txt
├── Procfile                # Railway start command
├── ASSUMPTIONS.md          # section 3, as a standalone deliverable
└── README.md               # setup, run, deploy, design notes
```

### Routes

| Method and path | Purpose |
|---|---|
| GET / | Client list with last report date (US1) |
| GET, POST /clients/new | Create a client profile (US1) |
| GET, POST /clients/{id}/edit | Edit a client profile (US1) |
| GET /clients/{id} | Client detail with report history (US1, US4) |
| POST /clients/{id}/generate | Create a draft report, pre-fill static data (US2) |
| GET, POST /reports/{id}/entry | Quarterly data entry with validation and live totals (US2) |
| GET /reports/{id}/sacs.pdf | Generate and download the SACS PDF (US3) |
| GET /reports/{id}/tcc.pdf | Generate and download the TCC PDF (US3) |
| GET /reports/{id}/download | Download both PDFs (US4) |
| POST /reports/{id}/export-canva | Optional Canva export, feature flagged (US4) |

### Layering

The calculation module is pure: functions take plain inputs and return computed values, with no knowledge of the data store or the PDF. The repository handles all data access behind one interface. The report HTML templates are populated with the calculation module's output and rendered to PDF by WeasyPrint, so the same markup drives both the on screen preview and the downloaded file. This separation means the business rules in section 6 are provable by unit tests in isolation, which directly serves the requirement that the app eliminates manual math errors.

---

## 10. PDF generation approach

Both reports are authored as HTML templates styled with CSS and rendered to vector PDF by WeasyPrint. Layout stability, the planner's "we want the form set so nothing can move," comes from a fixed `@page` size and absolute or grid positioning in CSS, not from free flowing content. The same template renders the on screen preview and the downloaded PDF, so what the team sees is what the client receives. The output is true vector PDF, so text stays crisp and selectable when printed for clients.

**SACS** is a fixed structure that does not vary between clients, so it is the simpler of the two. The green Inflow bubble, red Outflow bubble, blue Private Reserve section, and the connecting arrows are placed at fixed positions, with the dynamic numbers dropped into reserved slots. Circles are drawn with `border-radius: 50%`, arrows with CSS pseudo elements, so no coordinate math is needed. Page one carries the cashflow diagram, page two the Private Reserve balance, investment account balance, and target savings figure.

**TCC** is the variable case, since the number of account bubbles changes per client (one to six retirement per spouse, one to six non-retirement, zero to three liabilities). CSS grid handles this for free: fixed regions for retirement at the top, non-retirement at the bottom, trust in the center, and a separate liabilities section, with the account bubbles flowing into a grid inside each region. The page frame and the gray total boxes stay fixed while the grid absorbs however many bubbles a client needs, which is exactly the personalization the planner described, achieved without a custom layout engine.

Where the available cues do not fully determine the exact original look, the structure, colors, and grouping follow every described detail, and the README notes that pixel exact matching against the real sample PDFs would be a short follow up iteration.

---

## 11. Build sequence

1. Schema and repository layer, with seed data from the PRD example figures.
2. Calculation module and its full test suite, proving every rule in section 6 before any UI exists.
3. Client profile CRUD and the client list.
4. Report generation and the data entry form with validation and live totals.
5. SACS report HTML template and CSS, rendered to PDF with WeasyPrint.
6. TCC report HTML template with the CSS grid handling variable bubbles, rendered to PDF.
7. Download of both PDFs and report history.
8. Optional Canva export behind a feature flag.
9. README and ASSUMPTIONS finalised, Railway deployment.

---

## 12. Sprint implementation plan (two hour build)

Sections 5 through 11 describe the production target. This section is the deliberately scoped version built against a two hour clock for the take home, with a Loom walkthrough. The strategy is to demonstrate the full workflow end to end and narrate the production path for everything deferred. Each cut below is a choice, not an omission, and the narration makes that explicit.

### What is built and what is cut

The whole prototype runs as a minimal Flask app, because WeasyPrint is a Python library and needs a server to produce a downloadable file. Data is an in memory Python structure shaped exactly like the section 5 schema, sitting behind the single repository interface, so the swap to SQLite is a one file change rather than a rewrite. Two or three sample clients are pre seeded from the PRD example figures, one married couple with several accounts and one single client, which is enough to show variable layout.

The client profile create and edit screens (US1) are cut, because building that CRUD UI is the largest time sink and adds no demo value when the data can be pre seeded. Selecting a pre seeded client from a dropdown shows the same outcome. The data entry form, the live math, both reports, and PDF download are all built, because those are the core of the workflow and the parts worth seeing on camera.

Live totals are computed in the browser in JavaScript for snappy updates as balances are typed. The authoritative numbers placed into the PDF are recomputed server side in the pure Python calculation module at generation time, which WeasyPrint requires anyway, so the production correct "recompute server side to prevent tampering" pattern comes for free rather than as a promise. The calculation rules in section 6 still get their unit tests, because correctness is the heart of the assessment.

### Cut list with the production path for each

| Deferred for the sprint | Prototype substitute | Production path |
|---|---|---|
| SQLite persistence and migrations | In memory store behind the repository interface | Swap the one repository module to SQLite using the section 5 DDL |
| Client create and edit CRUD UI | Pre seeded sample clients, selected from a dropdown | Build the profile forms in section 4, US1 |
| Per keystroke server calculation | Live totals in browser JS | Already mirrored: server recomputes authoritatively at PDF generation |
| Canva export | Omitted, flagged as nice to have per the PRD | Feature flagged export route, section 9 |

### Reconstructed field inventory

Because the Data Point List document cannot be requested, the field labels below are reconstructed from the PRD's field descriptions, the key definitions table, and the User Story 3 acceptance criteria. They are the hardcoded UI labels for the data entry form and the report templates.

Static, from the client profile: client 1 and client 2 names, dates of birth, last four of SSN, marital status, monthly salary after tax, agreed monthly expense budget, insurance deductibles total, account list with type and last four, trust property address, liabilities with type and interest rate.

Dynamic, entered each quarter: per account balance (for example Roth IRA Balance, IRA Balance, 401K Balance, Schwab Brokerage Balance), cash balance for each investment account, Private Reserve Balance, Zillow Home Value, and each liability balance (for example Mortgage Balance, Auto Loan Balance).

Calculated and shown live, never entered: monthly excess (Inflow minus Outflow), Private Reserve target (six times expenses plus deductibles), each spouse's retirement total, non-retirement total (trust excluded), grand total net worth, and liabilities total (separate, never subtracted).

### Loom talking points

A short script that frames the cuts as judgment rather than gaps.

- "This is an AI Engineer test, and the right call was to build no AI, because the PRD says so three times. The value is accurate, deterministic reports, and I will show where AI earns its place in version two."
- "Persistence is an in memory store for this prototype to demonstrate the workflow. It sits behind one data accessor, so moving to the SQLite schema I designed is a single file change."
- "I reconstructed the field list from the PRD's field descriptions and acceptance criteria. The Data Point List would map these one to one to columns; here they are the form labels."
- "The math is mirrored in the browser for instant feedback, but the numbers in the PDF are recomputed server side, so they cannot be tampered with and cannot drift."
- "The reports are HTML and CSS rendered to vector PDF by WeasyPrint, which matches the recommended stack and keeps the layout locked, so nothing moves regardless of the numbers or the number of accounts."

---

## 13. Requirements traceability

Every PRD requirement mapped to where this document addresses it, for gap checking.

| PRD requirement | Addressed in |
|---|---|
| Client profile stored once (names, DOB, age, SSN last 4, accounts, salary, budget, reserve target) | US1, `clients` + `persons` + `accounts` tables |
| Single and married (Client 1 / Client 2) support | `persons.person_role`, `marital_status` |
| Account structure: retirement, non-retirement, trust, liabilities | `accounts`, `trusts`, `liabilities` tables |
| Edit client when things change | US1, profile edit route |
| Client list with last report date | US1, GET / route, derived from `reports` |
| One click Generate Report, pre-filled form | US2, POST /clients/{id}/generate |
| Dynamic fields show last value, use last value option | US2, report entry route querying prior report |
| Incomplete fields highlighted, cannot generate with missing data | US2, server side validation on report entry |
| Live totals as balances entered | US2, `entry.js` preview plus server side calc |
| SACS excess = inflow minus outflow | Section 6, `calculations.py` |
| Reserve target = 6 x expenses + deductibles | Section 6, `calculations.py` |
| Retirement totals per spouse | Section 6 |
| Non-retirement total excludes trust | Section 6, enforced by `trusts` being separate |
| Grand total = retirement + retirement + non-retirement + trust | Section 6 |
| Liabilities summed separately, never subtracted | Section 6, enforced structurally |
| SACS PDF layout: green/red/blue bubbles, arrows, header, two pages | US3, `templates/reports/sacs.html`, section 10 |
| TCC PDF layout: grouped accounts, info bubbles, gray totals, liabilities | US3, `templates/reports/tcc.html`, section 10 |
| Variable bubble count per client | CSS grid in `tcc.html`, section 10 |
| Fixed layout, nothing moves | Locked CSS and fixed `@page` via WeasyPrint, section 10 |
| Download both PDFs | US4, GET /reports/{id}/download |
| Export to Canva (optional) | US4, feature flagged export route |
| Report history re-download | US4, `reports` retained, history route |
| Company branding (blue) on reports; portal UI palette | Section 8, 60/30/10 rule and report semantic colors |
| No AI in V1 | Section 2, no model anywhere in scope |
| Stack: Railway, Python, HTML/CSS/JS, SQLite, WeasyPrint | Section 7 |
| Env vars CANVA_API_KEY, RAILWAY_DATABASE_PATH | Section 7 |

---

## 14. Out of scope for version one

Preserved from the PRD so nothing is lost: automated pulling from RightCapital, Schwab, Pinnacle Bank, and Zillow; a client facing expense worksheet on the portal; an onboarding automation agent; Plaid integration; Dropbox auto save; and monthly email distribution. These are version two candidates and are the natural homes for AI assistance once manual entry is replaced by ingestion.