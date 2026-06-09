import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

class CorporateDataGenerator:
    def __init__(self, num_employees=450, num_transactions=12200):
        self.num_employees = num_employees
        self.num_transactions = num_transactions
        self.regions = ['NA', 'EMEA', 'APAC', 'LATAM']
        self.departments = ['Field Sales', 'Corporate Marketing', 'Travel & Executive Admin', 'Software Engineering', 'HR & Recruitment', 'Supply Chain']

        self.mcc_directory = {
            '5812': ('Restaurants / Dining',       ['Local Steakhouse', 'Bistro Hub', 'Tokyo Dining Corp', 'London Tavern']),
            '5813': ('Bars / Taverns / Lounges',   ['Skyline Lounge', 'The Cocktail Grid', 'Downtown Pub', 'Shibuya Drinkery']),
            '7011': ('Hotels / Lodging',            ['Marriott International', 'Hilton Hotels', 'Business Stay Inn', 'Euro Lodging']),
            '4111': ('Commuter Transport',          ['Uber Inc', 'Lyft Ride', 'London Underground', 'NYC Transit']),
            '4816': ('Computer Services / SaaS',   ['AWS Cloud Services', 'GitHub Enterprise', 'Figma Design', 'Slack Technologies']),
            '5999': ('Misc. Retail / Office Supplies', ['Staples Corp', 'Office Depot', 'Amazon Business', 'Global Logistics Tech']),
            '7995': ('Gambling / Betting',         ['BetOnline Casino', 'Vegas Slot Network', 'CryptoWager Ltd']),
            '5921': ('Package Liquor Stores',      ['Vintage Wine & Spirits', 'Total Beverage Outlet', 'Liquor Express']),
            '7273': ('Adult Entertainment',        ['RedLight Venues', 'Escort Services Int']),
        }

        os.makedirs('data', exist_ok=True)
        os.makedirs('outputs', exist_ok=True)

        self.employees          = self._generate_employee_directory()
        self.travel_itineraries = []

    # ── EMPLOYEE DIRECTORY ────────────────────────────────────────────────────
    def _generate_employee_directory(self):
        employees   = {}
        dep_weights = [0.35, 0.15, 0.05, 0.25, 0.10, 0.10]
        for i in range(1, self.num_employees + 1):
            emp_id = f"EMP_{i:03d}"
            dept   = random.choices(self.departments, weights=dep_weights)[0]
            region = random.choice(self.regions)
            tier   = ('Tier_1_Exec'
                      if dept in ['Travel & Executive Admin', 'Field Sales'] or random.random() > 0.85
                      else 'Tier_2_Standard')
            limit  = 5000.00 if tier == 'Tier_1_Exec' else 3000.00
            employees[emp_id] = {
                'Department': dept, 'Region': region,
                'Card_Tier': tier, 'Single_Txn_Limit': limit
            }
        return employees

    # ── HELPER: get the next Saturday from a base date ────────────────────────
    @staticmethod
    def _next_weekend_day(base_dt):
        """Return a Saturday or Sunday on or after base_dt."""
        days_until = (5 - base_dt.weekday()) % 7     # days until Saturday (weekday 5)
        if days_until == 0 and random.random() > 0.5:
            days_until = 1                            # sometimes pick Sunday instead
        return base_dt + timedelta(days=days_until, hours=random.randint(10, 22))

    # ── MAIN BUILD ────────────────────────────────────────────────────────────
    def build_dataset(self):
        start_date      = datetime(2025, 1, 1)
        transactions    = []
        emp_ids         = list(self.employees.keys())
        whitelisted_mccs = ['5812', '7011', '4111', '4816', '5999']

        print("Generating core enterprise transactions...")
        for tx_idx in range(1, self.num_transactions + 1):
            tx_id    = f"TXN_{tx_idx:06d}"
            emp_id   = random.choice(emp_ids)
            emp_meta = self.employees[emp_id]
            timestamp = start_date + timedelta(minutes=random.randint(0, 525600))
            mcc       = random.choice(whitelisted_mccs)
            merchant  = random.choice(self.mcc_directory[mcc][1])

            if   mcc == '7011': amount = round(np.random.uniform(150, 800), 2)
            elif mcc == '4816': amount = round(np.random.uniform(20, 400), 2)
            elif mcc == '5812': amount = round(np.random.exponential(65), 2) + 10
            else:               amount = round(np.random.uniform(10, 150), 2)

            transactions.append({
                'Transaction_ID': tx_id, 'Employee_ID': emp_id,
                'Department': emp_meta['Department'], 'Region': emp_meta['Region'],
                'Card_Tier': emp_meta['Card_Tier'], 'Single_Txn_Limit': emp_meta['Single_Txn_Limit'],
                'Transaction_Timestamp': timestamp, 'Amount_USD': amount,
                'Merchant_Name': merchant, 'MCC': mcc, 'Injected_Anomaly': 'None'
            })

            # Build travel itinerary for hotel / dining transactions
            # High probability (~92%) so most organic weekend hospitality is covered
            if mcc in ['7011', '5812'] and random.random() > 0.08:
                self.travel_itineraries.append({
                    'Employee_ID':        emp_id,
                    'Destination_Region': emp_meta['Region'],
                    'Trip_Start': timestamp - timedelta(days=random.randint(1, 2)),
                    'Trip_End':   timestamp + timedelta(days=random.randint(2, 5)),
                })

        # ── ANOMALY INJECTION ─────────────────────────────────────────────────
        print("Injecting targeted policy leakage anomalies...")

        # R1 — Blacklist MCC (160 records)
        for _ in range(160):
            emp_id   = random.choice(emp_ids)
            emp_meta = self.employees[emp_id]
            mcc      = random.choice(['7995', '5921', '7273'])
            transactions.append({
                'Transaction_ID':    f"TXN_R1_{random.randint(1000,9999)}",
                'Employee_ID':       emp_id,
                'Department':        emp_meta['Department'],
                'Region':            emp_meta['Region'],
                'Card_Tier':         emp_meta['Card_Tier'],
                'Single_Txn_Limit':  emp_meta['Single_Txn_Limit'],
                'Transaction_Timestamp': start_date + timedelta(minutes=random.randint(0, 525600)),
                'Amount_USD':        round(np.random.uniform(120, 1400), 2),
                'Merchant_Name':     random.choice(self.mcc_directory[mcc][1]),
                'MCC':               mcc,
                'Injected_Anomaly':  'RULE_01_BLACKLIST',
            })

        # R2 — Transaction Splitting (80 pairs = 160 records)
        for _ in range(80):
            emp_id    = random.choice(emp_ids)
            emp_meta  = self.employees[emp_id]
            limit     = emp_meta['Single_Txn_Limit']
            base_time = start_date + timedelta(minutes=random.randint(0, 525600))
            for offset, amt in zip(
                [0, 12],
                [round(limit * random.uniform(0.45, 0.55), 2),
                 round(limit * random.uniform(0.45, 0.55), 2)]
            ):
                transactions.append({
                    'Transaction_ID':    f"TXN_R2_{random.randint(10000,99999)}",
                    'Employee_ID':       emp_id,
                    'Department':        emp_meta['Department'],
                    'Region':            emp_meta['Region'],
                    'Card_Tier':         emp_meta['Card_Tier'],
                    'Single_Txn_Limit':  limit,
                    'Transaction_Timestamp': base_time + timedelta(minutes=offset),
                    'Amount_USD':        amt,
                    'Merchant_Name':     'AWS Cloud Services',
                    'MCC':               '4816',
                    'Injected_Anomaly':  'RULE_02_SPLIT',
                })

        # R3 — Weekend Overage, NO travel, amount > $250 (140 records)
        # Hospitality MCC, genuine weekend (Saturday/Sunday), no travel itinerary injected
        for _ in range(140):
            emp_id    = random.choice(emp_ids)
            emp_meta  = self.employees[emp_id]
            base      = start_date + timedelta(weeks=random.randint(0, 51))
            weekend_ts = self._next_weekend_day(base)
            mcc       = random.choice(['5812', '7011'])
            transactions.append({
                'Transaction_ID':    f"TXN_R3_{random.randint(1000,9999)}",
                'Employee_ID':       emp_id,
                'Department':        emp_meta['Department'],
                'Region':            emp_meta['Region'],
                'Card_Tier':         emp_meta['Card_Tier'],
                'Single_Txn_Limit':  emp_meta['Single_Txn_Limit'],
                'Transaction_Timestamp': weekend_ts,
                'Amount_USD':        round(np.random.uniform(265, 800), 2),
                'Merchant_Name':     random.choice(self.mcc_directory[mcc][1]),
                'MCC':               mcc,
                'Injected_Anomaly':  'RULE_03_WEEKEND_OVERAGE',
                # NOTE: No travel itinerary added for these employees on these dates
            })

        # R4 — Single Transaction Limit Breach, weekday, non-blacklist (60 records)
        for _ in range(60):
            emp_id    = random.choice(emp_ids)
            emp_meta  = self.employees[emp_id]
            limit     = emp_meta['Single_Txn_Limit']
            # Pick a weekday timestamp
            base      = start_date + timedelta(days=random.randint(0, 364))
            # Shift to weekday if needed
            while base.weekday() >= 5:
                base += timedelta(days=1)
            mcc = random.choice(['4816', '5999', '4111', '7011'])
            transactions.append({
                'Transaction_ID':    f"TXN_R4_{random.randint(1000,9999)}",
                'Employee_ID':       emp_id,
                'Department':        emp_meta['Department'],
                'Region':            emp_meta['Region'],
                'Card_Tier':         emp_meta['Card_Tier'],
                'Single_Txn_Limit':  limit,
                'Transaction_Timestamp': base + timedelta(hours=random.randint(9, 18)),
                'Amount_USD':        round(limit * random.uniform(1.05, 1.12), 2),
                'Merchant_Name':     random.choice(self.mcc_directory[mcc][1]),
                'MCC':               mcc,
                'Injected_Anomaly':  'RULE_04_LIMIT_BREACH',
            })

        # R5 — Weekend spend, no travel OR on travel but non-hospitality MCC (140 records)
        # Split: 70 with no travel (under $250), 70 on travel with non-hospitality MCC
        for i in range(140):
            emp_id    = random.choice(emp_ids)
            emp_meta  = self.employees[emp_id]
            base      = start_date + timedelta(weeks=random.randint(0, 51))
            weekend_ts = self._next_weekend_day(base)

            if i < 70:
                # Scenario A: No travel, weekend, under $250 → R5
                amount = round(np.random.uniform(30, 245), 2)
                mcc    = random.choice(['5812', '7011'])
                transactions.append({
                    'Transaction_ID':    f"TXN_R5A_{random.randint(1000,9999)}",
                    'Employee_ID':       emp_id,
                    'Department':        emp_meta['Department'],
                    'Region':            emp_meta['Region'],
                    'Card_Tier':         emp_meta['Card_Tier'],
                    'Single_Txn_Limit':  emp_meta['Single_Txn_Limit'],
                    'Transaction_Timestamp': weekend_ts,
                    'Amount_USD':        amount,
                    'Merchant_Name':     random.choice(self.mcc_directory[mcc][1]),
                    'MCC':               mcc,
                    'Injected_Anomaly':  'RULE_05_NO_TRAVEL_LOW_VALUE',
                })
            else:
                # Scenario B: On travel, weekend, but NON-hospitality MCC → R5
                mcc = random.choice(['4816', '5999', '4111'])
                transactions.append({
                    'Transaction_ID':    f"TXN_R5B_{random.randint(1000,9999)}",
                    'Employee_ID':       emp_id,
                    'Department':        emp_meta['Department'],
                    'Region':            emp_meta['Region'],
                    'Card_Tier':         emp_meta['Card_Tier'],
                    'Single_Txn_Limit':  emp_meta['Single_Txn_Limit'],
                    'Transaction_Timestamp': weekend_ts,
                    'Amount_USD':        round(np.random.uniform(50, 400), 2),
                    'Merchant_Name':     random.choice(self.mcc_directory[mcc][1]),
                    'MCC':               mcc,
                    'Injected_Anomaly':  'RULE_05_TRAVEL_NON_HOSPITALITY',
                })
                # Add travel itinerary covering this weekend for scenario B
                self.travel_itineraries.append({
                    'Employee_ID':        emp_id,
                    'Destination_Region': emp_meta['Region'],
                    'Trip_Start': weekend_ts - timedelta(days=1),
                    'Trip_End':   weekend_ts + timedelta(days=2),
                })

        # ── SAVE ──────────────────────────────────────────────────────────────
        df_ledger = pd.DataFrame(transactions)
        df_travel = pd.DataFrame(self.travel_itineraries).drop_duplicates()

        df_ledger.to_csv('data/corporate_card_ledger.csv', index=False)
        df_travel.to_csv('data/approved_travel_itineraries.csv', index=False)

        injected = (df_ledger['Injected_Anomaly'] != 'None').sum()
        print(f"\nData generation complete.")
        print(f"  Total records      : {len(df_ledger):,}")
        print(f"  Injected anomalies : {injected} ({injected/len(df_ledger)*100:.1f}%)")
        print(f"  Travel itineraries : {len(df_travel):,}")
        print(f"\n  Breakdown:")
        print(df_ledger['Injected_Anomaly'].value_counts().to_string())
        print("\nFiles written to data/")


if __name__ == "__main__":
    generator = CorporateDataGenerator()
    generator.build_dataset()
