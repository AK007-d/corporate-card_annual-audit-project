# EXECUTIVE STRATEGIC REPORT: ANNUAL SPEND COMPLIANCE & FORENSIC AUDIT
**Project Title:** GlobalSpend Insights: Corporate Card Policy Enforcement & Context-Aware Audit Pipeline
**Reporting Period:** FY 2025  |  **Engine Version:** R1–R5 Multi-Rule Compliance Framework

---

## 1. Executive Summary

An end-to-end automated policy compliance audit was executed across the enterprise's global
commercial card network. The engine evaluated **12,860** card transactions representing
**$3,021,049.00** in total spend across 6 departments and 4 global regions.

| KPI | Value |
|-----|-------|
| Total Transactions Analysed | 12,860 |
| Total Portfolio Spend | $3,021,049.00 |
| Flagged Transactions | 949 (7.4% of volume) |
| Total Financial Exposure | $731,576.42 (24.2% of spend) |
| Compliance Rules Applied | 5 (R1 Blacklist · R2 Split · R3 Weekend · R4 Limit · R5 Context) |

---

## 2. Rule-by-Rule Violation Analysis

| Rule | Flag | Violations | Exposure (USD) | % of All Violations |
|------|------|-----------|---------------|---------------------|
| R1 — Blacklist MCC | FLAG_R1_BLACKLIST | 160 | $121,247.47 | 16.86% |
| R2 — Split Transaction | FLAG_R2_SPLIT | 92 | $185,005.53 | 9.69% |
| R3 — Weekend Overage | FLAG_R3_WEEKEND_OVERAGE | 159 | $81,981.52 | 16.75% |
| R4 — Limit Breach | FLAG_R4_LIMIT_BREACH | 60 | $267,781.01 | 6.32% |
| R5 — Context Fail | FLAG_R5_CONTEXT_FAIL | 478 | $75,560.89 | 50.37% |

### R5 Context Fail — Two Distinct Scenarios
R5 flags two different compliance failures:
- **No travel approval + weekend spend under $250** — low-value but contextually suspicious, requires manual review
- **On approved travel but non-hospitality MCC on weekend** — travel is approved but the spend category is outside expected hospitality (dining/hotels), requires manual review

Both scenarios are documented with reasons in `outputs/flag_r5_reconciliation_report.csv`.

---

## 3. Department Risk Profile

| Department | Total Claims | Exposure (USD) | Violation Rate | Exposure Rate |
|-----------|-------------|---------------|---------------|--------------|
| Field Sales | 4,793 | $333,153.22 | 7.55% | 27.08% |
| Software Engineering | 3,395 | $162,052.12 | 7.54% | 21.31% |
| Corporate Marketing | 1,746 | $87,044.13 | 8.19% | 22.57% |
| HR & Recruitment | 1,222 | $71,437.19 | 6.38% | 25.88% |
| Supply Chain | 1,225 | $47,372.95 | 6.2% | 19.05% |
| Travel & Executive Admin | 479 | $30,516.81 | 7.1% | 25.43% |

**Highest exposure:** Field Sales ($333,153.22) — primarily driven by
transaction splitting and blacklist MCC violations.

---

## 4. Strategic Recommendations

### R1 — Implement Network-Level MCC Hard Blocks
- **Finding:** 160 transactions at blocked MCCs (7995 Gambling,
  5921 Liquor, 7273 Adult Entertainment) totalling $121,247.47
- **Recommendation:** Move enforcement to point-of-sale via card issuer MCC hard blocks.
  Eliminate post-payment reconciliation for these categories entirely.
- **Impact:** 100% elimination of R1 exposure — $121,247.47 recovered

### R2 — Role-Based Spend Tiers to Eliminate Split Evasion
- **Finding:** 92 split transaction pairs detected, primarily in
  Software Engineering splitting SaaS subscriptions to bypass the $3,000 limit.
- **Recommendation:** Increase single-transaction ceiling to $5,000 for Software Engineering
  Leads at whitelisted technology vendors (MCC 4816). Removes the incentive to split.
- **Impact:** ~85% reduction in R2 volume — ~$157,254.70 exposure resolved

### R3 — Enforce Weekend Hospitality Policy with Clear Communication
- **Finding:** 159 weekend transactions exceeding the $250 standard
  limit with no approved travel context, totalling $81,981.52
- **Recommendation:** Automate pre-approval workflow for weekend hospitality spend above $250.
  Employee must submit business justification before the weekend, not after.
- **Impact:** Shifts burden from audit to pre-approval — reduces R3 leakage significantly

### R4 — Enforce Hard Decline for Limit Breaches at Point of Sale
- **Finding:** 60 transactions exceeded the cardholder's
  Single_Txn_Limit, generating $267,781.01 in unauthorised exposure.
- **Recommendation:** Card issuer should enforce hard declines for transactions exceeding
  tier-based limits. Current system allows post-transaction flags — too late.
- **Impact:** 100% prevention of R4 exposure — $267,781.01 protected

### R5 — Build Context-Aware Authorization via Travel API Integration
- **Finding:** 478 weekend transactions flagged for context failure:
  either no travel approval or non-hospitality spend while on travel.
- **Recommendation:** Connect card authorization to HR travel management system via API.
  Dynamically adjust spend context based on active travel itinerary status. Non-hospitality
  weekend spend should trigger real-time SMS confirmation regardless of travel status.
- **Impact:** Eliminates false positives for legitimate travel while catching genuine misuse

---

## 5. Projected Impact Matrix

| Recommendation | Rule | Exposure Addressable | Expected Outcome |
|---------------|------|---------------------|-----------------|
| MCC Hard Blocks | R1 | $121,247.47 | Full Elimination |
| Role-Based Tiers | R2 | ~$157,254.70 | ~85% Reduction |
| Weekend Pre-Approval | R3 | $81,981.52 | Structural Control |
| Hard Decline Enforcement | R4 | $267,781.01 | Full Prevention |
| Travel API Integration | R5 | $75,560.89 | Context-Aware Automation |

---

## 6. Next Steps

1. **Week 1–2:** Activate R1 MCC hard blocks via card issuer configuration
2. **Week 3–4:** Configure role-based spend tiers for Software Engineering (R2)
3. **Month 2:** Deploy weekend pre-approval workflow (R3)
4. **Month 2–3:** Implement hard decline enforcement for limit breaches (R4)
5. **Month 3–4:** Integrate HR travel API for context-aware authorization (R5)
6. **Ongoing:** Re-run compliance engine monthly; track flag reduction rates

---

*Dashboard: `outputs/global_compliance_dashboard.png`*
*Reconciliation: `outputs/flag_r5_reconciliation_report.csv`*
*Engine: R1–R5 Multi-Rule Compliance Framework | FY 2025*
