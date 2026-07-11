"""
Agent Demo: Lineage-Aware Memory Governance Walkthrough
=========================================================

Demonstrates the AMU mechanism end-to-end against a real SQLite database.

Scenario
--------
  1. Finance agent computes a high-value-customer segment by joining
     customers.income (SENSITIVE) against transactions.amount.
  2. Finance writes the result as an AMU, with full lineage.
  3. Marketing agent requests the SAME metric.
  4. The lineage gate BLOCKS the retrieval (Marketing cannot see 'income').
  5. Marketing falls back to its own in-scope recompute (no income join).
  6. Finance computes a SAFE metric (no sensitive columns).
  7. Marketing retrieves the safe metric from memory -- reuse succeeds.

Run:  python examples/agent_demo/demo.py
Writes a readable transcript to examples/agent_demo/transcript.md
"""

import os
import sqlite3
import tempfile
from datetime import datetime

from amu_governance import AMU, GovernancePolicy, Lineage, LineageStep, LineageAwareSystem

DB_PATH = os.path.join(tempfile.gettempdir(), "amu_demo.db")
TRANSCRIPT_PATH = os.path.join(os.path.dirname(__file__), "transcript.md")

POLICY = GovernancePolicy(
    sensitive_columns={"income"},
    department_permissions={
        "Finance": {"customer_id", "income", "region", "txn_id", "amount", "txn_date"},
        "Marketing": {"customer_id", "region", "txn_id", "amount", "txn_date"},  # no income
    },
)

CUSTOMER_DATA = [
    (1, "Alice Chen", "EUROPE", 120_000),
    (2, "Bob Okafor", "AMERICA", 45_000),
    (3, "Clara Schmidt", "EUROPE", 310_000),
    (4, "David Park", "ASIA", 82_000),
    (5, "Eva Martinez", "AMERICA", 250_000),
]

TRANSACTION_DATA = [
    (1, 1, 4_500, "2026-03-01"),
    (2, 1, 12_000, "2026-04-15"),
    (3, 2, 800, "2026-04-20"),
    (4, 3, 25_000, "2026-02-10"),
    (5, 3, 18_000, "2026-05-05"),
    (6, 4, 3_200, "2026-03-22"),
    (7, 5, 15_000, "2026-01-18"),
    (8, 5, 22_000, "2026-04-30"),
]

INCOME_THRESHOLD = 100_000
SPEND_THRESHOLD = 5_000


def setup_database() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS transactions;

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            region      TEXT NOT NULL,
            income      REAL NOT NULL   -- SENSITIVE
        );

        CREATE TABLE transactions (
            txn_id      INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            amount      REAL NOT NULL,
            txn_date    TEXT NOT NULL
        );
        """
    )
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMER_DATA)
    cur.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?)", TRANSACTION_DATA)
    conn.commit()
    conn.close()


def finance_compute_high_value_segment(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.customer_id, c.name, c.income, SUM(t.amount) AS total_spend
        FROM customers c JOIN transactions t ON c.customer_id = t.customer_id
        WHERE c.income > ?
        GROUP BY c.customer_id, c.name, c.income
        HAVING SUM(t.amount) > ?
        ORDER BY c.customer_id
        """,
        (INCOME_THRESHOLD, SPEND_THRESHOLD),
    )
    rows = cur.fetchall()
    lineage = Lineage(
        steps=(
            LineageStep("customers", ("customer_id", "income", "region")),
            LineageStep("transactions", ("customer_id", "amount", "txn_date")),
        ),
        filter_logic=f"income > {INCOME_THRESHOLD} AND total_spend > {SPEND_THRESHOLD}",
    )
    return {"count": len(rows), "rows": rows, "lineage": lineage}


def marketing_compute_high_value_segment_inscope(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.customer_id, c.name, c.region, SUM(t.amount) AS total_spend
        FROM customers c JOIN transactions t ON c.customer_id = t.customer_id
        GROUP BY c.customer_id, c.name, c.region
        HAVING SUM(t.amount) > 10000
        ORDER BY c.customer_id
        """
    )
    rows = cur.fetchall()
    lineage = Lineage(
        steps=(
            LineageStep("customers", ("customer_id", "region")),
            LineageStep("transactions", ("customer_id", "amount", "txn_date")),
        ),
        filter_logic="total_spend > 10000 (no income — Marketing in-scope)",
    )
    return {"count": len(rows), "rows": rows, "lineage": lineage}


def finance_compute_order_volume(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(amount) FROM transactions")
    count, total = cur.fetchone()
    lineage = Lineage(
        steps=(LineageStep("transactions", ("txn_id", "amount", "txn_date")),),
        filter_logic="all transactions, no filter",
    )
    return {"count": count, "total": round(total, 2), "lineage": lineage}


def run_demo() -> None:
    lines = ["# Lineage-Aware Memory Governance — Agent Demo Transcript",
             f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*", ""]

    setup_database()
    conn = sqlite3.connect(DB_PATH)
    memory = LineageAwareSystem(POLICY)
    epoch = 0

    print("[1] Finance computes high_value_segment (touches income)...")
    fin = finance_compute_high_value_segment(conn)
    fin_amu = AMU("high_value_segment", float(fin["count"]), "Finance", fin["lineage"], epoch)
    epoch += 1
    memory.write(fin_amu)
    print(f"    sensitivity_tags={fin_amu.sensitivity_tags(POLICY)} definition_hash={fin_amu.definition_hash}")
    lines.append(f"## Step 1: Finance writes `high_value_segment`\n"
                 f"sensitivity_tags = `{fin_amu.sensitivity_tags(POLICY)}`, "
                 f"definition_hash = `{fin_amu.definition_hash}`")

    print("[2] Marketing requests high_value_segment...")
    mkt_fallback = marketing_compute_high_value_segment_inscope(conn)
    mkt_amu = AMU("high_value_segment", float(mkt_fallback["count"]), "Marketing", mkt_fallback["lineage"], epoch)
    epoch += 1
    result = memory.request("high_value_segment", "Marketing", mkt_amu)
    status = "BLOCKED -> Marketing falls back to in-scope recompute" if result.blocked else "SERVED (unexpected)"
    print(f"    {status}: {mkt_fallback['count']} customers (spend-only definition)")
    conflict = memory.write(mkt_amu)
    print(f"    Marketing AMU written. Definition conflict with Finance: {conflict}")
    lines.append(f"\n## Step 2: Marketing requests `high_value_segment`\n"
                 f"Result: **{status}**. Conflict with Finance's definition: `{conflict}`\n"
                 f"(Finance hash `{fin_amu.definition_hash}` vs Marketing hash `{mkt_amu.definition_hash}`)")

    print("[3] Finance computes order_volume (no sensitive columns)...")
    safe = finance_compute_order_volume(conn)
    safe_amu = AMU("order_volume", safe["total"], "Finance", safe["lineage"], epoch)
    epoch += 1
    memory.write(safe_amu)
    lines.append(f"\n## Step 3: Finance writes `order_volume`\n"
                 f"sensitivity_tags = `{safe_amu.sensitivity_tags(POLICY)}` (empty)")

    print("[4] Marketing requests order_volume...")
    result2 = memory.request("order_volume", "Marketing", safe_amu)
    print(f"    {'SERVED from memory (reuse)' if result2.reused else 'Recomputed (unexpected)'}: "
          f"${safe_amu.value:,.2f}")
    lines.append(f"\n## Step 4: Marketing requests `order_volume`\n"
                 f"Result: **{'SERVED from memory' if result2.reused else 'recomputed'}**, "
                 f"value = `${safe_amu.value:,.2f}`")

    lines.append("\n## Summary\n"
                  "| Step | Metric | Requester | Outcome |\n"
                  "|---|---|---|---|\n"
                  "| 1 | high_value_segment | — | Finance writes (income-derived) |\n"
                  f"| 2 | high_value_segment | Marketing | {status} |\n"
                  "| 3 | order_volume | — | Finance writes (no sensitive columns) |\n"
                  f"| 4 | order_volume | Marketing | {'served from memory' if result2.reused else 'recomputed'} |")

    conn.close()
    with open(TRANSCRIPT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"\nTranscript written to {TRANSCRIPT_PATH}")


if __name__ == "__main__":
    run_demo()
