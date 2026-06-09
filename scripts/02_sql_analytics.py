"""
02_sql_analytics.py
-------------------
Runs all SQL analysis queries against the compliance-flagged database.
Outputs 7 CSV files + R5 reconciliation report to outputs/
"""

import sqlite3
import pandas as pd
import os

DB_PATH    = 'data/enterprise_spend.db'
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run():
    conn = sqlite3.connect(DB_PATH)
    print("=" * 60)
    print("SQL ANALYTICS PIPELINE")
    print("=" * 60)

    # ── Q1: Department Compliance Scorecard ───────────────────────────────────
    q1 = pd.read_sql_query("""
        SELECT
            Department,
            COUNT(*)                                                          AS Total_Claims,
            ROUND(SUM(Amount_USD), 2)                                         AS Total_Spend_USD,
            SUM(CASE WHEN System_Audit_Flag != 'CLEAN' THEN 1 ELSE 0 END)    AS Violations,
            ROUND(
                CAST(SUM(CASE WHEN System_Audit_Flag != 'CLEAN' THEN 1 ELSE 0 END) AS FLOAT)
                / COUNT(*) * 100, 2)                                          AS Violation_Rate_Pct,
            ROUND(SUM(CASE WHEN System_Audit_Flag != 'CLEAN'
                           THEN Amount_USD ELSE 0 END), 2)                    AS Exposure_USD,
            ROUND(
                SUM(CASE WHEN System_Audit_Flag != 'CLEAN' THEN Amount_USD ELSE 0 END)
                / SUM(Amount_USD) * 100, 2)                                   AS Exposure_Rate_Pct
        FROM corporate_card_ledger
        GROUP BY Department
        ORDER BY Exposure_USD DESC;
    """, conn)
    q1.to_csv(f'{OUTPUT_DIR}/q1_dept_compliance.csv', index=False)
    print("\n[Q1] Department Compliance Scorecard")
    print(q1.to_string(index=False))

    # ── Q2: Monthly Trend Analysis ────────────────────────────────────────────
    q2 = pd.read_sql_query("""
        SELECT
            strftime('%Y-%m', Transaction_Timestamp)                          AS Month,
            COUNT(*)                                                          AS Total_Volume,
            ROUND(SUM(Amount_USD), 2)                                         AS Total_Spend,
            SUM(CASE WHEN System_Audit_Flag != 'CLEAN' THEN 1 ELSE 0 END)    AS Leaked_Volume,
            ROUND(SUM(CASE WHEN System_Audit_Flag != 'CLEAN'
                           THEN Amount_USD ELSE 0 END), 2)                    AS Leaked_Spend,
            ROUND(
                CAST(SUM(CASE WHEN System_Audit_Flag != 'CLEAN' THEN 1 ELSE 0 END) AS FLOAT)
                / COUNT(*) * 100, 2)                                          AS Volume_Leakage_Pct,
            ROUND(
                SUM(CASE WHEN System_Audit_Flag != 'CLEAN' THEN Amount_USD ELSE 0 END)
                / SUM(Amount_USD) * 100, 2)                                   AS Spend_Leakage_Pct
        FROM corporate_card_ledger
        GROUP BY Month
        ORDER BY Month ASC;
    """, conn)
    q2.to_csv(f'{OUTPUT_DIR}/q2_monthly_trend.csv', index=False)
    print(f"\n[Q2] Monthly Trend — {len(q2)} months exported")

    # ── Q3: Top 15 High-Risk Employees ────────────────────────────────────────
    q3 = pd.read_sql_query("""
        SELECT
            Employee_ID,
            Department,
            Region,
            COUNT(*)                  AS Total_Violations,
            ROUND(SUM(Amount_USD), 2) AS Flagged_Spend_USD,
            GROUP_CONCAT(DISTINCT System_Audit_Flag) AS Flag_Types
        FROM corporate_card_ledger
        WHERE System_Audit_Flag != 'CLEAN'
        GROUP BY Employee_ID
        ORDER BY Flagged_Spend_USD DESC
        LIMIT 15;
    """, conn)
    q3.to_csv(f'{OUTPUT_DIR}/q3_high_risk_employees.csv', index=False)
    print(f"\n[Q3] Top 15 High-Risk Employees exported")

    # ── Q4: Violation Breakdown by Flag Type ──────────────────────────────────
    q4 = pd.read_sql_query("""
        SELECT
            System_Audit_Flag                                                 AS Violation_Type,
            COUNT(*)                                                          AS Transaction_Count,
            ROUND(SUM(Amount_USD), 2)                                         AS Exposure_USD,
            ROUND(SUM(Amount_USD) * 100.0
                / (SELECT SUM(Amount_USD) FROM corporate_card_ledger), 2)     AS Pct_Of_Total_Spend
        FROM corporate_card_ledger
        GROUP BY System_Audit_Flag
        ORDER BY Exposure_USD DESC;
    """, conn)
    q4.to_csv(f'{OUTPUT_DIR}/q4_violation_by_type.csv', index=False)
    print("\n[Q4] Violation Breakdown by Flag Type")
    print(q4.to_string(index=False))

    # ── Q5: SLA Simulation Matrix ─────────────────────────────────────────────
    q5 = pd.read_sql_query("""
        SELECT
            Region,
            System_Audit_Flag                                                 AS Risk_Vector,
            COUNT(*)                                                          AS Backlog_Tickets,
            CASE
                WHEN COUNT(*) > 300 THEN 'CAPACITY_BREACHED'
                WHEN COUNT(*) > 150 THEN 'WARNING'
                ELSE 'WITHIN_CAPACITY'
            END                                                               AS SLA_Risk_Status
        FROM corporate_card_ledger
        WHERE System_Audit_Flag != 'CLEAN'
        GROUP BY Region, System_Audit_Flag
        ORDER BY Backlog_Tickets DESC;
    """, conn)
    q5.to_csv(f'{OUTPUT_DIR}/q5_sla_simulation.csv', index=False)
    print(f"\n[Q5] SLA Simulation Matrix exported")

    # ── Q6: Split Transaction Evasion Footprints ──────────────────────────────
    q6 = pd.read_sql_query("""
        SELECT
            Employee_ID,
            Merchant_Name,
            ROUND(Amount_USD, 2)      AS Amount_USD,
            Transaction_Timestamp,
            Department,
            Region,
            System_Audit_Flag
        FROM corporate_card_ledger
        WHERE System_Audit_Flag = 'FLAG_R2_SPLIT'
        ORDER BY Employee_ID, Transaction_Timestamp;
    """, conn)
    q6.to_csv(f'{OUTPUT_DIR}/q6_detected_evasion_footprints.csv', index=False)
    print(f"\n[Q6] Split Transaction Footprints — {len(q6)} records exported")

    # ── Q7: Audit Rule Impact Summary ─────────────────────────────────────────
    q7 = pd.read_sql_query("""
        SELECT
            System_Audit_Flag                                                 AS Audit_Rule,
            COUNT(*)                                                          AS Violations_Caught,
            ROUND(SUM(Amount_USD), 2)                                         AS Exposure_USD,
            ROUND(COUNT(*) * 100.0
                / (SELECT COUNT(*) FROM corporate_card_ledger
                   WHERE System_Audit_Flag != 'CLEAN'), 2)                    AS Pct_Of_All_Violations
        FROM corporate_card_ledger
        WHERE System_Audit_Flag != 'CLEAN'
        GROUP BY System_Audit_Flag
        ORDER BY Exposure_USD DESC;
    """, conn)
    q7.to_csv(f'{OUTPUT_DIR}/q7_audit_rule_impact.csv', index=False)
    print("\n[Q7] Audit Rule Impact Summary")
    print(q7.to_string(index=False))

    # ── R5 RECONCILIATION REPORT ──────────────────────────────────────────────
    # All weekend transactions with full resolution status + reason
    r5_report = pd.read_sql_query("""
        SELECT
            l.Transaction_ID,
            l.Employee_ID,
            l.Department,
            l.Region,
            l.Transaction_Timestamp,
            l.Amount_USD,
            l.Merchant_Name,
            l.MCC,
            l.R5_Reason                                                       AS Context_Fail_Reason,
            'MANUAL REVIEW REQUIRED'                                          AS Action_Required
        FROM corporate_card_ledger l
        WHERE l.System_Audit_Flag = 'FLAG_R5_CONTEXT_FAIL'
        ORDER BY l.Department, l.Employee_ID, l.Transaction_Timestamp;
    """, conn)
    r5_report.to_csv(f'{OUTPUT_DIR}/flag_r5_reconciliation_report.csv', index=False)

    # Print R5 reconciliation summary
    print("\n[R5] Weekend Transaction Reconciliation Report")
    print(f"     Total weekend transactions : {len(r5_report):,}")
    print(f"     Reason breakdown:")
    summary = r5_report['Context_Fail_Reason'].value_counts()
    for reason, cnt in summary.items():
        print(f"       {reason[:70]:<70} {cnt:>5}")
    print(f"\n     Saved → {OUTPUT_DIR}/flag_r5_reconciliation_report.csv")

    conn.close()
    print("\n" + "=" * 60)
    print("✓ SQL analytics complete. Run 03_executive_report.py next.")
    print("=" * 60)


if __name__ == "__main__":
    run()
