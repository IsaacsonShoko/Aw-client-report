# Assumptions

Recorded because the source documents (Data Point List, sample PDFs, screenshots) could not be requested per the test guidelines. Each is a defensible reading of the PRD.

1. **Money is stored as integer cents.** Avoids floating point error in a tool whose entire purpose is accurate numbers.
2. **Derived values are never persisted.** Age, monthly excess, all section totals, the grand total, and the reserve target are computed on read, so they cannot drift out of agreement.
3. **Report history is preserved by snapshot.** Each generated report stores a snapshot of the salary, expense budget, and insurance deductibles in force at generation time, so re-downloading a past quarter reproduces the original numbers even after the profile changes.
4. **The reserve target is calculated, with an optional manual override.** The PRD calls it both static profile data and a calculated value. It is computed as six times monthly expenses plus total insurance deductibles, with a nullable override field for the rare case the team sets it manually.
5. **The $1,000 floor is a global constant** held in application config, not a per client field, since the PRD states it never changes.
6. **The trust is a separate entity, not an account,** so its exclusion from the non-retirement total is structural rather than a rule that must be remembered in code.
7. **Authoritative calculation is server side.** The data entry form shows live totals in the browser for usability, but the numbers placed in the PDF are always recomputed server side by the same calculation module.
8. **Canva export is treated as optional.** The PRD flags it as a nice to have and notes the planner would prefer the portal itself. PDF download is built as the core path; Canva export is scaffolded behind a feature flag (not implemented in the 2-hour sprint).
9. **Final PDF layout is matched structurally, not pixel for pixel,** because the original sample PDFs are not available in the assessment. Colors, grouping, and field placement follow every described cue.
