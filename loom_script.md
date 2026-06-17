# Loom Walkthrough Script (AW Client Report Portal)

**Time:** Under 2 minutes.

**[0:00 - 0:20] The Strategy & Scope**
"Hi Ritchelle and team, here is my build for the AW Client Report Portal. 
First, I noticed the PRD explicitly asks for *no AI* in version one. The real challenge here is data stability and perfectly fixed PDF layouts. So, I built exactly that—a deterministic, bulletproof portal. I deferred AI for a future ingestion phase, as trying to force an LLM into pure arithmetic right now would be the wrong engineering choice."

**[0:20 - 0:45] The Prototype Constraints & Architecture**
"To respect the two-hour sprint, I pre-seeded the database with an in-memory repository. This way, swapping to SQLite in production is just a single file change. 
The application runs on Flask. All the core arithmetic—like the reserve target and net worth—is completely isolated in a pure Python calculation module that I fully unit-tested to ensure zero manual math errors."

**[0:45 - 1:20] Live Demo: Data Entry & Live Math**
*(Screen recording: Show the Client List -> Click 'Generate Report' -> Data Entry Form)*
"When generating a report, the data entry form pre-fills the static profile data. 
As I type in the balances, you'll see the totals on the right—like the Retirement totals and Grand Total Net Worth—updating live via JavaScript. This gives the team instant feedback and catches errors.
But importantly, when we generate the PDF, the server *recomputes* everything authoritatively to guarantee data integrity."

**[1:20 - 1:50] Live Demo: PDF Generation & Fixed Layouts**
*(Screen recording: Click 'Save and Generate PDFs' -> Open SACS and TCC PDFs)*
"Finally, we use WeasyPrint to render our HTML and CSS directly to PDF. 
By using fixed `@page` sizing and CSS Grid, we ensure the TCC account bubbles and SACS diagrams are perfectly locked in place. The layout never shifts, whether a client has two accounts or ten.
All files are pushed to Railway for easy deployment. Thanks for the opportunity!"