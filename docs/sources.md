# Source List — Groww Fee Explainer (Milestone 5)

Official, public, **no-login** URLs that ground the fee explainer.
The generated explainer injects exactly **two** of them (the two marked ✅, per the brief).

Every URL below was opened and confirmed to resolve on the date in the *Date checked* column.

| # | Source | URL | What it supports | Date checked | Used in explainer |
|---|---|---|---|---|---|
| 1 | AMFI — Expense Ratio (Investor Corner) | https://www.amfiindia.com/investor/knowledge-center-info?zoneName=expenseRatio | What the Total Expense Ratio (TER) is, its components, and the SEBI Regulation 52 limits | 2026-10-15 | ✅ |
| 2 | SEBI Investor — Exit Load | https://investor.sebi.gov.in/exit_load.html | Definition of exit load, how it reduces the redemption amount, and a worked example | 2026-10-15 | ✅ |
| 3 | SEBI — Investor Education | https://investor.sebi.gov.in/ | Regulator's plain-language investor-education portal (charges, TER, fees) | 2026-10-15 | — |
| 4 | Groww — Exit Load in Mutual Funds | https://groww.in/p/exit-load-in-mutual-funds | Groww's product-level explainer: what exit load is, how it is calculated, and the SIP nuance | 2026-10-15 | — |
| 5 | Groww — Pricing & Charges | https://groww.in/pricing | Groww's official published brokerage / DP / AMC / statutory charges | 2026-10-15 | — |
| 6 | NSE — Investor's Home (Investor Education) | https://www.nseindia.com/static/invest/investors-home | Exchange investor-education hub (investing safely, charges & taxes) | 2026-10-15 | — |

**Last checked: 2026-10-15**

## Coverage (per brief)

- **AMFI** — mutual-fund charges / TER ✅ (source 1)
- **SEBI** — investor education **and** exit load ✅ (sources 2, 3)
- **Groww official pricing / charges page** ✅ (source 5, plus the exit-load explainer, source 4)
- **Exchange investor-education page** ✅ (source 6 — NSE)
- **Total: 6 URLs** (within the required 4–6 range)

> **Why AMFI is not the exit-load link:** AMFI's old knowledge-centre exit-load URL
> (`amfiindia.com/investor-corner/knowledge-center/exit-load.html`) now returns **404**, and AMFI
> has no live replacement exit-load page. AMFI's currently-live charge page is cited instead and the
> exit-load definition is grounded in SEBI's investor-education exit-load page. Every link above was
> checked to resolve on 2026-10-15.

> The links are defined in `src/config.py` → `SOURCES` (the explainer reads them from there).
> Keep this table in sync with that list.
