"""
03_executive_report.py
----------------------
Generates the executive compliance dashboard (PNG) and QBR markdown report.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import os
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── PALETTE ───────────────────────────────────────────────────────────────────
C_R1 = '#BB0000'   # Blacklist  — deep red
C_R2 = '#E76500'   # Split      — orange
C_R3 = '#F0C040'   # Weekend    — amber
C_R4 = '#7B2D8B'   # Limit      — purple
C_R5 = '#4272B0'   # Context    — blue
C_OK = '#107E3E'   # Clean      — green
C_BG = '#F5F6F7'
C_DK = '#1D2D3E'
C_GR = '#6E7D8C'

FLAG_COLORS = {
    'FLAG_R1_BLACKLIST':       C_R1,
    'FLAG_R2_SPLIT':           C_R2,
    'FLAG_R3_WEEKEND_OVERAGE': C_R3,
    'FLAG_R4_LIMIT_BREACH':    C_R4,
    'FLAG_R5_CONTEXT_FAIL':    C_R5,
    'CLEAN':                   C_OK,
}

FLAG_LABELS = {
    'FLAG_R1_BLACKLIST':       'R1 Blacklist MCC',
    'FLAG_R2_SPLIT':           'R2 Split Transaction',
    'FLAG_R3_WEEKEND_OVERAGE': 'R3 Weekend Overage',
    'FLAG_R4_LIMIT_BREACH':    'R4 Limit Breach',
    'FLAG_R5_CONTEXT_FAIL':    'R5 Context Fail',
    'CLEAN':                   'Clean',
}

def fmt_usd(x, _=None):
    return f'${x/1_000:.0f}K' if x >= 1000 else f'${x:.0f}'


def generate():
    print('=' * 60)
    print('EXECUTIVE REPORT GENERATOR')
    print('=' * 60)

    df        = pd.read_csv('data/corporate_card_ledger.csv')
    q1        = pd.read_csv(f'{OUTPUT_DIR}/q1_dept_compliance.csv')
    q2        = pd.read_csv(f'{OUTPUT_DIR}/q2_monthly_trend.csv')
    q3        = pd.read_csv(f'{OUTPUT_DIR}/q3_high_risk_employees.csv')
    q4        = pd.read_csv(f'{OUTPUT_DIR}/q4_violation_by_type.csv')
    q7        = pd.read_csv(f'{OUTPUT_DIR}/q7_audit_rule_impact.csv')

    df_flagged = df[df['System_Audit_Flag'] != 'CLEAN']

    total_spend    = df['Amount_USD'].sum()
    total_txns     = len(df)
    leakage_spend  = df_flagged['Amount_USD'].sum()
    leakage_txns   = len(df_flagged)
    leakage_rate   = leakage_spend / total_spend * 100
    txn_rate       = leakage_txns  / total_txns  * 100

    # ── FIGURE SETUP ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(22, 28), facecolor=C_BG)
    fig.text(0.5, 0.983, 'GlobalSpend Insights: Corporate Card Governance & Audit Dashboard',
             ha='center', fontsize=20, fontweight='bold', color=C_DK)
    fig.text(0.5, 0.975, 'Multi-Rule Compliance Engine  |  R1–R5 Policy Enforcement  |  FY 2025',
             ha='center', fontsize=11, color=C_GR)

    # KPI banner
    kpis = [
        (f'{total_txns:,}',         'Total Transactions'),
        (f'${total_spend:,.0f}',    'Total Spend'),
        (f'{leakage_txns:,}',       'Flagged Transactions'),
        (f'${leakage_spend:,.0f}',  'Financial Exposure'),
        (f'{leakage_rate:.1f}%',    'Spend Leakage Rate'),
        (f'{txn_rate:.1f}%',        'Transaction Leakage Rate'),
    ]
    for i, (val, lbl) in enumerate(kpis):
        x = 0.05 + i * 0.155
        fig.text(x + 0.035, 0.965, val, ha='center', fontsize=13,
                 fontweight='bold', color='#0070F2')
        fig.text(x + 0.035, 0.957, lbl, ha='center', fontsize=8, color=C_GR)

    fig.add_artist(plt.Line2D([0.04, 0.96], [0.952, 0.952],
                   transform=fig.transFigure, color=C_GR, lw=0.8))

    gs = fig.add_gridspec(3, 2, left=0.06, right=0.96,
                          top=0.945, bottom=0.04,
                          hspace=0.40, wspace=0.28)

    # ── CHART 1: Department Exposure ──────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    dept_s = q1.sort_values('Exposure_USD', ascending=True)
    short  = [d[:28] for d in dept_s['Department']]
    bars   = ax1.barh(short, dept_s['Exposure_USD'],
                      color='#C44E52', edgecolor='white', height=0.6)
    for bar, val in zip(bars, dept_s['Exposure_USD']):
        ax1.text(bar.get_width() + 2000, bar.get_y() + bar.get_height()/2,
                 fmt_usd(val), va='center', fontsize=8, color=C_DK)
    ax1.set_xlabel('Exposure (USD)', fontsize=9)
    ax1.set_title('Financial Leakage Exposure by Department',
                  fontweight='bold', fontsize=11, color=C_DK, pad=8)
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    ax1.set_facecolor(C_BG)
    ax1.spines[['top','right']].set_visible(False)
    ax1.tick_params(labelsize=8)

    # ── CHART 2: Risk Vector Breakdown (all 5 flags) ──────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    flags_only = q4[q4['Violation_Type'] != 'CLEAN'].sort_values('Exposure_USD', ascending=True)
    bar_colors = [FLAG_COLORS.get(f, C_GR) for f in flags_only['Violation_Type']]
    bars2 = ax2.barh(
        [FLAG_LABELS.get(f, f) for f in flags_only['Violation_Type']],
        flags_only['Exposure_USD'],
        color=bar_colors, edgecolor='white', height=0.6)
    for bar, val in zip(bars2, flags_only['Exposure_USD']):
        ax2.text(bar.get_width() + 2000, bar.get_y() + bar.get_height()/2,
                 fmt_usd(val), va='center', fontsize=8, color=C_DK)
    ax2.set_xlabel('Exposure (USD)', fontsize=9)
    ax2.set_title('Risk Exposure by Policy Rule Vector (R1–R5)',
                  fontweight='bold', fontsize=11, color=C_DK, pad=8)
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    ax2.set_facecolor(C_BG)
    ax2.spines[['top','right']].set_visible(False)
    ax2.tick_params(labelsize=8)

    # ── CHART 3: Monthly Leakage Trend ────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    months = q2['Month'].tolist()
    x_idx  = range(len(months))
    ax3.bar(x_idx, q2['Leaked_Spend'], color='#C44E52', alpha=0.5,
            width=0.7, label='Monthly Leakage ($)')
    ax3b = ax3.twinx()
    ax3b.plot(x_idx, q2['Spend_Leakage_Pct'], color=C_R1, lw=2.2,
              marker='o', ms=4, label='Leakage %')
    ax3b.axhline(y=q2['Spend_Leakage_Pct'].mean(), color=C_R2,
                 ls='--', lw=1.2, alpha=0.8)
    ax3.set_xticks(list(x_idx))
    ax3.set_xticklabels([m[-5:] for m in months], rotation=45,
                        ha='right', fontsize=7)
    ax3.set_ylabel('Leakage ($)', fontsize=9, color='#C44E52')
    ax3b.set_ylabel('Leakage (%)', fontsize=9, color=C_R1)
    ax3.set_title('Monthly Financial Leakage Trend',
                  fontweight='bold', fontsize=11, color=C_DK, pad=8)
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    ax3.set_facecolor(C_BG)
    ax3.spines[['top']].set_visible(False)
    ax3.tick_params(axis='y', labelsize=8)
    ax3b.tick_params(axis='y', labelsize=8)
    lines = [mpatches.Patch(color='#C44E52', alpha=0.5, label='Monthly Leakage ($)'),
             mpatches.Patch(color=C_R1, label='Leakage %')]
    ax3.legend(handles=lines, fontsize=7, loc='upper right', framealpha=0.5)

    # ── CHART 4: Top 10 High-Risk Employees ───────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    top10 = q3.head(10).sort_values('Flagged_Spend_USD', ascending=True)
    emp_labels = [f"{e} ({d[:10]})" for e, d in
                  zip(top10['Employee_ID'], top10['Department'])]
    bars4 = ax4.barh(emp_labels, top10['Flagged_Spend_USD'],
                     color=C_R4, alpha=0.8, edgecolor='white', height=0.6)
    for bar, val in zip(bars4, top10['Flagged_Spend_USD']):
        ax4.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
                 fmt_usd(val), va='center', fontsize=8, color=C_DK)
    ax4.set_xlabel('Flagged Spend (USD)', fontsize=9)
    ax4.set_title('Top 10 High-Risk Employees by Flagged Spend',
                  fontweight='bold', fontsize=11, color=C_DK, pad=8)
    ax4.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    ax4.set_facecolor(C_BG)
    ax4.spines[['top','right']].set_visible(False)
    ax4.tick_params(labelsize=8)

    # ── CHART 5: Portfolio Health — Count vs Volume (dual donut) ─────────────
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.axis('off')
    ax5.set_title('Portfolio Health Balance: Transaction Count vs Dollar Volume',
                  fontweight='bold', fontsize=11, color=C_DK, pad=8)

    ax5a = fig.add_subplot(3, 4, 9)
    count_data   = [total_txns - leakage_txns, leakage_txns]
    ax5a.pie(count_data,
             labels=['Clean\nSwipes', 'Flagged\nSwipes'],
             autopct='%1.1f%%',
             colors=[C_OK, C_R1],
             startangle=90, explode=(0, 0.08),
             wedgeprops=dict(width=0.55),
             textprops={'fontsize': 8, 'fontweight': 'bold'})
    ax5a.set_title('By Count', fontsize=9, fontweight='bold')

    ax5b = fig.add_subplot(3, 4, 10)
    vol_data = [total_spend - leakage_spend, leakage_spend]
    ax5b.pie(vol_data,
             labels=['Clean\nCash', 'Flagged\nCash'],
             autopct='%1.1f%%',
             colors=[C_OK, C_R1],
             startangle=90, explode=(0, 0.08),
             wedgeprops=dict(width=0.55),
             textprops={'fontsize': 8, 'fontweight': 'bold'})
    ax5b.set_title('By Volume ($)', fontsize=9, fontweight='bold')

    # ── CHART 6: Regional Risk Distribution ───────────────────────────────────
    ax6 = fig.add_subplot(gs[2, 1])
    region_data = df_flagged.groupby(['Region', 'System_Audit_Flag'])[
        'Amount_USD'].sum().unstack(fill_value=0)
    region_data = region_data[[c for c in FLAG_COLORS if c in region_data.columns
                                and c != 'CLEAN']]
    region_data.plot(
        kind='bar', ax=ax6, stacked=True,
        color=[FLAG_COLORS[c] for c in region_data.columns],
        edgecolor='white', width=0.6)
    ax6.set_xlabel('Region', fontsize=9)
    ax6.set_ylabel('Exposure (USD)', fontsize=9)
    ax6.set_title('Regional Risk Profile — Stacked by Rule Vector',
                  fontweight='bold', fontsize=11, color=C_DK, pad=8)
    ax6.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    ax6.set_facecolor(C_BG)
    ax6.spines[['top','right']].set_visible(False)
    ax6.tick_params(axis='x', rotation=0, labelsize=9)
    ax6.tick_params(axis='y', labelsize=8)
    handles = [mpatches.Patch(color=FLAG_COLORS[c], label=FLAG_LABELS[c])
               for c in region_data.columns]
    ax6.legend(handles=handles, fontsize=7, loc='upper right', framealpha=0.5)

    fig.text(0.5, 0.022,
             'GlobalSpend Insights  |  5-Rule Compliance Engine  |  '
             'R1: Blacklist · R2: Split · R3: Weekend Overage · '
             'R4: Limit Breach · R5: Context Fail',
             ha='center', fontsize=8, color=C_GR, style='italic')

    dash_path = f'{OUTPUT_DIR}/global_compliance_dashboard.png'
    plt.savefig(dash_path, dpi=150, bbox_inches='tight',
                facecolor=C_BG, edgecolor='none')
    plt.close()
    print(f'[✓] Dashboard saved → {dash_path}')

    # ── MARKDOWN QBR REPORT ───────────────────────────────────────────────────
    r1_row = q7[q7['Audit_Rule']=='FLAG_R1_BLACKLIST'].iloc[0]
    r2_row = q7[q7['Audit_Rule']=='FLAG_R2_SPLIT'].iloc[0]
    r3_row = q7[q7['Audit_Rule']=='FLAG_R3_WEEKEND_OVERAGE'].iloc[0]
    r4_row = q7[q7['Audit_Rule']=='FLAG_R4_LIMIT_BREACH'].iloc[0]
    r5_row = q7[q7['Audit_Rule']=='FLAG_R5_CONTEXT_FAIL'].iloc[0]

    top_dept     = q1.iloc[0]
    second_dept  = q1.iloc[1]

    report = f"""# EXECUTIVE STRATEGIC REPORT: ANNUAL SPEND COMPLIANCE & FORENSIC AUDIT
**Project Title:** GlobalSpend Insights: Corporate Card Policy Enforcement & Context-Aware Audit Pipeline
**Reporting Period:** FY 2025  |  **Engine Version:** R1–R5 Multi-Rule Compliance Framework

---

## 1. Executive Summary

An end-to-end automated policy compliance audit was executed across the enterprise's global
commercial card network. The engine evaluated **{total_txns:,}** card transactions representing
**${total_spend:,.2f}** in total spend across 6 departments and 4 global regions.

| KPI | Value |
|-----|-------|
| Total Transactions Analysed | {total_txns:,} |
| Total Portfolio Spend | ${total_spend:,.2f} |
| Flagged Transactions | {leakage_txns:,} ({txn_rate:.1f}% of volume) |
| Total Financial Exposure | ${leakage_spend:,.2f} ({leakage_rate:.1f}% of spend) |
| Compliance Rules Applied | 5 (R1 Blacklist · R2 Split · R3 Weekend · R4 Limit · R5 Context) |

---

## 2. Rule-by-Rule Violation Analysis

| Rule | Flag | Violations | Exposure (USD) | % of All Violations |
|------|------|-----------|---------------|---------------------|
| R1 — Blacklist MCC | FLAG_R1_BLACKLIST | {int(r1_row.Violations_Caught)} | ${r1_row.Exposure_USD:,.2f} | {r1_row.Pct_Of_All_Violations}% |
| R2 — Split Transaction | FLAG_R2_SPLIT | {int(r2_row.Violations_Caught)} | ${r2_row.Exposure_USD:,.2f} | {r2_row.Pct_Of_All_Violations}% |
| R3 — Weekend Overage | FLAG_R3_WEEKEND_OVERAGE | {int(r3_row.Violations_Caught)} | ${r3_row.Exposure_USD:,.2f} | {r3_row.Pct_Of_All_Violations}% |
| R4 — Limit Breach | FLAG_R4_LIMIT_BREACH | {int(r4_row.Violations_Caught)} | ${r4_row.Exposure_USD:,.2f} | {r4_row.Pct_Of_All_Violations}% |
| R5 — Context Fail | FLAG_R5_CONTEXT_FAIL | {int(r5_row.Violations_Caught)} | ${r5_row.Exposure_USD:,.2f} | {r5_row.Pct_Of_All_Violations}% |

### R5 Context Fail — Two Distinct Scenarios
R5 flags two different compliance failures:
- **No travel approval + weekend spend under $250** — low-value but contextually suspicious, requires manual review
- **On approved travel but non-hospitality MCC on weekend** — travel is approved but the spend category is outside expected hospitality (dining/hotels), requires manual review

Both scenarios are documented with reasons in `outputs/flag_r5_reconciliation_report.csv`.

---

## 3. Department Risk Profile

| Department | Total Claims | Exposure (USD) | Violation Rate | Exposure Rate |
|-----------|-------------|---------------|---------------|--------------|
{chr(10).join(f"| {r.Department} | {r.Total_Claims:,} | ${r.Exposure_USD:,.2f} | {r.Violation_Rate_Pct}% | {r.Exposure_Rate_Pct}% |" for _, r in q1.iterrows())}

**Highest exposure:** {top_dept.Department} (${top_dept.Exposure_USD:,.2f}) — primarily driven by
transaction splitting and blacklist MCC violations.

---

## 4. Strategic Recommendations

### R1 — Implement Network-Level MCC Hard Blocks
- **Finding:** {int(r1_row.Violations_Caught)} transactions at blocked MCCs (7995 Gambling,
  5921 Liquor, 7273 Adult Entertainment) totalling ${r1_row.Exposure_USD:,.2f}
- **Recommendation:** Move enforcement to point-of-sale via card issuer MCC hard blocks.
  Eliminate post-payment reconciliation for these categories entirely.
- **Impact:** 100% elimination of R1 exposure — ${r1_row.Exposure_USD:,.2f} recovered

### R2 — Role-Based Spend Tiers to Eliminate Split Evasion
- **Finding:** {int(r2_row.Violations_Caught)} split transaction pairs detected, primarily in
  Software Engineering splitting SaaS subscriptions to bypass the $3,000 limit.
- **Recommendation:** Increase single-transaction ceiling to $5,000 for Software Engineering
  Leads at whitelisted technology vendors (MCC 4816). Removes the incentive to split.
- **Impact:** ~85% reduction in R2 volume — ~${r2_row.Exposure_USD*0.85:,.2f} exposure resolved

### R3 — Enforce Weekend Hospitality Policy with Clear Communication
- **Finding:** {int(r3_row.Violations_Caught)} weekend transactions exceeding the $250 standard
  limit with no approved travel context, totalling ${r3_row.Exposure_USD:,.2f}
- **Recommendation:** Automate pre-approval workflow for weekend hospitality spend above $250.
  Employee must submit business justification before the weekend, not after.
- **Impact:** Shifts burden from audit to pre-approval — reduces R3 leakage significantly

### R4 — Enforce Hard Decline for Limit Breaches at Point of Sale
- **Finding:** {int(r4_row.Violations_Caught)} transactions exceeded the cardholder's
  Single_Txn_Limit, generating ${r4_row.Exposure_USD:,.2f} in unauthorised exposure.
- **Recommendation:** Card issuer should enforce hard declines for transactions exceeding
  tier-based limits. Current system allows post-transaction flags — too late.
- **Impact:** 100% prevention of R4 exposure — ${r4_row.Exposure_USD:,.2f} protected

### R5 — Build Context-Aware Authorization via Travel API Integration
- **Finding:** {int(r5_row.Violations_Caught)} weekend transactions flagged for context failure:
  either no travel approval or non-hospitality spend while on travel.
- **Recommendation:** Connect card authorization to HR travel management system via API.
  Dynamically adjust spend context based on active travel itinerary status. Non-hospitality
  weekend spend should trigger real-time SMS confirmation regardless of travel status.
- **Impact:** Eliminates false positives for legitimate travel while catching genuine misuse

---

## 5. Projected Impact Matrix

| Recommendation | Rule | Exposure Addressable | Expected Outcome |
|---------------|------|---------------------|-----------------|
| MCC Hard Blocks | R1 | ${r1_row.Exposure_USD:,.2f} | Full Elimination |
| Role-Based Tiers | R2 | ~${r2_row.Exposure_USD*0.85:,.2f} | ~85% Reduction |
| Weekend Pre-Approval | R3 | ${r3_row.Exposure_USD:,.2f} | Structural Control |
| Hard Decline Enforcement | R4 | ${r4_row.Exposure_USD:,.2f} | Full Prevention |
| Travel API Integration | R5 | ${r5_row.Exposure_USD:,.2f} | Context-Aware Automation |

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
"""

    report_path = f'{OUTPUT_DIR}/Executive_QBR_Compliance_Report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'[✓] QBR Report saved  → {report_path}')

    print('\n' + '=' * 60)
    print('✓ Executive report complete.')
    print('  All outputs saved to outputs/')
    print('=' * 60)


if __name__ == '__main__':
    generate()
