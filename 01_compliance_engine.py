"""
01_compliance_engine.py
-----------------------
Applies the full 5-rule compliance decision tree to the corporate card ledger.

Decision Tree:
──────────────
ALL TRANSACTIONS
│
├── R1: MCC in blacklist (7995, 5921, 7273)?
│   YES → FLAG_R1_BLACKLIST. Stop.
│
├── R2: Same employee + same merchant + within 30 mins
│       + each txn < Single_Txn_Limit but combined > limit?
│   YES → FLAG_R2_SPLIT. Stop.
│
├── WEEKEND (Saturday=5 or Sunday=6)?
│   YES → On approved travel itinerary?
│         YES → Hospitality MCC (5812, 5813, 7011)?
│               YES → Amount ≤ Single_Txn_Limit?
│                     YES → CLEAN  (logged as APPROVED_BY_TRAVEL_REGISTRY)
│                     NO  → FLAG_R4_LIMIT_BREACH
│               NO  → FLAG_R5_CONTEXT_FAIL
│                     reason: "On travel, non-hospitality weekend spend"
│         NO  → Amount > $250?
│               YES → FLAG_R3_WEEKEND_OVERAGE
│               NO  → FLAG_R5_CONTEXT_FAIL
│                     reason: "No travel approval, weekend spend under $250"
│
└── WEEKDAY + still CLEAN?
    └── Amount > Single_Txn_Limit?
        YES → FLAG_R4_LIMIT_BREACH
        NO  → CLEAN
"""

import pandas as pd
import numpy as np
import sqlite3
import os

BLACKLIST_MCC    = {7995, 5921, 7273}
HOSPITALITY_MCC  = {5812, 5813, 7011}
WEEKEND_STD_LIMIT = 250.00


class ComplianceEngine:
    def __init__(self,
                 ledger_path='data/corporate_card_ledger.csv',
                 travel_path='data/approved_travel_itineraries.csv'):
        self.ledger_path = ledger_path
        self.travel_path = travel_path
        self.db_path     = 'data/enterprise_spend.db'

        print("=" * 60)
        print("COMPLIANCE ENGINE — Loading data")
        print("=" * 60)

        self.df = pd.read_csv(self.ledger_path)
        self.df_travel = pd.read_csv(self.travel_path)

        self.df['Transaction_Timestamp'] = pd.to_datetime(self.df['Transaction_Timestamp'])
        self.df_travel['Trip_Start']     = pd.to_datetime(self.df_travel['Trip_Start'])
        self.df_travel['Trip_End']       = pd.to_datetime(self.df_travel['Trip_End'])

        # Reset flags to CLEAN before re-evaluation
        self.df['System_Audit_Flag'] = 'CLEAN'
        self.df['R5_Reason']         = ''

        print(f"  Records loaded     : {len(self.df):,}")
        print(f"  Travel itineraries : {len(self.df_travel):,}")

    # ── R1: BLACKLIST MCC ─────────────────────────────────────────────────────
    def _apply_r1(self):
        mask = self.df['MCC'].isin(BLACKLIST_MCC)
        self.df.loc[mask, 'System_Audit_Flag'] = 'FLAG_R1_BLACKLIST'
        count = mask.sum()
        print(f"\n[R1] Blacklist MCC flagged       : {count:>5}")
        return count

    # ── R2: TRANSACTION SPLITTING ─────────────────────────────────────────────
    def _apply_r2(self):
        """
        Detect split transactions:
        Same employee + same merchant + within 30 minutes +
        each amount < Single_Txn_Limit but combined > limit.
        Only runs on CLEAN records (R1 already stopped).
        """
        clean = self.df[self.df['System_Audit_Flag'] == 'CLEAN'].copy()
        clean = clean.sort_values(['Employee_ID', 'Merchant_Name', 'Transaction_Timestamp'])

        clean['prev_time'] = clean.groupby(
            ['Employee_ID', 'Merchant_Name'])['Transaction_Timestamp'].shift(1)
        clean['prev_amt']  = clean.groupby(
            ['Employee_ID', 'Merchant_Name'])['Amount_USD'].shift(1)
        clean['prev_id']   = clean.groupby(
            ['Employee_ID', 'Merchant_Name'])['Transaction_ID'].shift(1)

        clean['mins_apart'] = (
            clean['Transaction_Timestamp'] - clean['prev_time']
        ).dt.total_seconds() / 60

        split_mask = (
            clean['prev_time'].notna() &
            (clean['Amount_USD']  < clean['Single_Txn_Limit']) &
            (clean['prev_amt']    < clean['Single_Txn_Limit']) &
            ((clean['Amount_USD'] + clean['prev_amt']) > clean['Single_Txn_Limit']) &
            (clean['mins_apart'] <= 30)
        )

        split_pairs = clean[split_mask]
        flagged_ids = set(split_pairs['Transaction_ID'].tolist() +
                          split_pairs['prev_id'].dropna().tolist())

        self.df.loc[self.df['Transaction_ID'].isin(flagged_ids),
                    'System_Audit_Flag'] = 'FLAG_R2_SPLIT'

        count = len(flagged_ids)
        print(f"[R2] Split transactions flagged  : {count:>5}")
        return count

    # ── BUILD TRAVEL LOOKUP ───────────────────────────────────────────────────
    def _build_travel_lookup(self):
        """
        Returns a set of (Employee_ID, date) tuples where the employee
        has an approved travel itinerary covering that date.
        """
        lookup = set()
        for _, row in self.df_travel.iterrows():
            emp_id     = row['Employee_ID']
            trip_start = row['Trip_Start'].date()
            trip_end   = row['Trip_End'].date()
            current    = trip_start
            while current <= trip_end:
                lookup.add((emp_id, current))
                current += pd.Timedelta(days=1)
        return lookup

    # ── R3 / R4 / R5: WEEKEND BRANCH + R4 WEEKDAY ────────────────────────────
    def _apply_weekend_and_r4(self, travel_lookup):
        """
        Processes all CLEAN records through the weekend branch
        and then catches weekday limit breaches as R4.
        Also populates R5_Reason for context audit trail.
        """
        clean_idx = self.df['System_Audit_Flag'] == 'CLEAN'
        clean     = self.df[clean_idx].copy()

        clean['_date']      = clean['Transaction_Timestamp'].dt.date
        clean['_dayofweek'] = clean['Transaction_Timestamp'].dt.dayofweek  # Mon=0 … Sun=6
        clean['_is_weekend']= clean['_dayofweek'].isin([5, 6])
        clean['_on_travel'] = clean.apply(
            lambda r: (r['Employee_ID'], r['_date']) in travel_lookup, axis=1)

        r3_ids = []; r4_ids = []; r5_ids = []; r5_reasons = {}

        for idx, row in clean.iterrows():
            if row['_is_weekend']:
                # ── WEEKEND BRANCH ────────────────────────────────────────
                if row['_on_travel']:
                    if row['MCC'] in HOSPITALITY_MCC:
                        if row['Amount_USD'] <= row['Single_Txn_Limit']:
                            pass  # CLEAN — APPROVED_BY_TRAVEL_REGISTRY
                        else:
                            r4_ids.append(idx)
                    else:
                        r5_ids.append(idx)
                        r5_reasons[idx] = (
                            f"Active travel itinerary found but MCC {row['MCC']} "
                            f"({row['Merchant_Name']}) is not a hospitality category "
                            f"— manual review required"
                        )
                else:
                    # Only flag hospitality MCCs for R3/R5 on weekends
                    # Non-hospitality weekend spend (transport, SaaS, retail)
                    # is normal and falls through to R4 check below
                    if row['MCC'] in HOSPITALITY_MCC:
                        if row['Amount_USD'] > WEEKEND_STD_LIMIT:
                            r3_ids.append(idx)
                        else:
                            r5_ids.append(idx)
                            r5_reasons[idx] = (
                                f"No approved travel itinerary on {row['_date']} "
                                f"— weekend hospitality spend of ${row['Amount_USD']:.2f} "
                                f"under ${WEEKEND_STD_LIMIT:.0f} limit, manual review required"
                            )
                    else:
                        # Non-hospitality, no travel, weekend — check limit only
                        if row['Amount_USD'] > row['Single_Txn_Limit']:
                            r4_ids.append(idx)
            else:
                # ── WEEKDAY BRANCH ────────────────────────────────────────
                if row['Amount_USD'] > row['Single_Txn_Limit']:
                    r4_ids.append(idx)

        self.df.loc[r3_ids, 'System_Audit_Flag'] = 'FLAG_R3_WEEKEND_OVERAGE'
        self.df.loc[r4_ids, 'System_Audit_Flag'] = 'FLAG_R4_LIMIT_BREACH'
        self.df.loc[r5_ids, 'System_Audit_Flag'] = 'FLAG_R5_CONTEXT_FAIL'

        for idx, reason in r5_reasons.items():
            self.df.loc[idx, 'R5_Reason'] = reason

        print(f"[R3] Weekend overage flagged     : {len(r3_ids):>5}")
        print(f"[R4] Limit breach flagged        : {len(r4_ids):>5}")
        print(f"[R5] Context fail flagged        : {len(r5_ids):>5}")
        return len(r3_ids), len(r4_ids), len(r5_ids)

    # ── TRAVEL REGISTRY ANNOTATION ────────────────────────────────────────────
    def _annotate_travel_approved(self, travel_lookup):
        """
        Tag CLEAN weekend hospitality transactions as APPROVED_BY_TRAVEL_REGISTRY
        in a separate column for the reconciliation report.
        """
        clean   = self.df['System_Audit_Flag'] == 'CLEAN'
        weekend = self.df['Transaction_Timestamp'].dt.dayofweek.isin([5, 6])
        hosp    = self.df['MCC'].isin(HOSPITALITY_MCC)

        candidates = self.df[clean & weekend & hosp].copy()
        candidates['_date'] = candidates['Transaction_Timestamp'].dt.date

        approved_idx = candidates[
            candidates.apply(
                lambda r: (r['Employee_ID'], r['_date']) in travel_lookup, axis=1)
        ].index

        self.df['Travel_Registry_Status'] = ''
        self.df.loc[approved_idx, 'Travel_Registry_Status'] = 'APPROVED_BY_TRAVEL_REGISTRY'

    # ── SAVE TO CSV + SQLITE ──────────────────────────────────────────────────
    def _save(self):
        save_df = self.df.copy()
        save_df['Transaction_Timestamp'] = save_df[
            'Transaction_Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        save_df.to_csv('data/corporate_card_ledger.csv', index=False)

        conn = sqlite3.connect(self.db_path)
        save_df.to_sql('corporate_card_ledger', conn, if_exists='replace', index=False)
        self.df_travel.to_sql('approved_travel_itineraries', conn,
                               if_exists='replace', index=False)
        conn.close()

        print(f"\n  CSV  → data/corporate_card_ledger.csv")
        print(f"  DB   → data/enterprise_spend.db")

    # ── RUN FULL PIPELINE ─────────────────────────────────────────────────────
    def run(self):
        print("\nApplying compliance rules...")
        self._apply_r1()
        self._apply_r2()

        print("\nBuilding travel lookup index...")
        travel_lookup = self._build_travel_lookup()
        print(f"  Travel coverage entries: {len(travel_lookup):,} employee-days")

        self._apply_weekend_and_r4(travel_lookup)
        self._annotate_travel_approved(travel_lookup)
        self._save()

        # ── Summary ──────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("FINAL FLAG DISTRIBUTION")
        print("=" * 60)
        dist = self.df['System_Audit_Flag'].value_counts()
        for flag, cnt in dist.items():
            pct = cnt / len(self.df) * 100
            print(f"  {flag:<30} {cnt:>5}  ({pct:.1f}%)")

        total_flagged = (self.df['System_Audit_Flag'] != 'CLEAN').sum()
        total_exposure = self.df.loc[
            self.df['System_Audit_Flag'] != 'CLEAN', 'Amount_USD'].sum()
        print(f"\n  Total flagged  : {total_flagged:,}")
        print(f"  Total exposure : ${total_exposure:,.2f}")
        print("=" * 60)
        print("\n✓ Compliance engine complete. Run 02_sql_analytics.py next.")


if __name__ == "__main__":
    engine = ComplianceEngine()
    engine.run()
