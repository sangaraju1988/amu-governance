"""
Automatic table/column lineage extraction from SQL, using sqlglot.

This module removes the need for an agent to self-report which columns it
touched: the executed SQL is parsed and its lineage is extracted directly
from the AST. Feed the output into Lineage/LineageStep (see model.py) to
build an AMU with a ground-truth derivation path.

Handles JOINs, subqueries, CTEs, table aliases, and quoted/space-containing
table names. Defaults to the SQLite dialect; override with `dialect=`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Set

import sqlglot
import sqlglot.expressions as exp

from .model import Lineage, LineageStep


def _normalize(name: str) -> str:
    """Lowercase, strip quotes/brackets, collapse whitespace to underscores."""
    name = name.strip().strip('"').strip("'").strip("[").strip("]")
    return re.sub(r"\s+", "_", name.lower())


def extract_lineage_from_sql(sql: str, dialect: str = "sqlite") -> List[Dict[str, object]]:
    """Parse `sql` and return per-table column sets.

    Returns a list of dicts: ``[{"table": str, "columns": List[str]}]``,
    suitable for converting directly into LineageStep objects via
    `lineage_from_sql`. Unqualified column references in a multi-table
    query that cannot be resolved to a single table are bucketed under the
    synthetic table name "unknown" rather than dropped -- an unresolved
    reference to a sensitive column (e.g. a comma-join `SELECT income FROM
    customer_pii c, transactions t WHERE ...`) must still surface in
    sensitivity checks, or the gate would silently under-report lineage and
    serve a result it should have blocked. Fail closed: an unresolved
    column counts as touched, never as absent.

    Never raises: on unparseable SQL, returns an empty list so a bad query
    never crashes the caller.
    """
    if not sql or not sql.strip():
        return []

    try:
        statement = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return []

    # Build alias -> real table name map.
    alias_to_table: Dict[str, str] = {}
    for table_expr in statement.find_all(exp.Table):
        real_name = _normalize(table_expr.name or "")
        alias = _normalize(table_expr.alias or "")
        alias_to_table[real_name] = real_name
        if alias and alias != real_name:
            alias_to_table[alias] = real_name

    # Collect columns per resolved table.
    table_cols: Dict[str, Set[str]] = defaultdict(set)
    for col_expr in statement.find_all(exp.Column):
        col_name = _normalize(col_expr.name or "")
        if not col_name or col_name == "*":
            continue

        table_ref = _normalize(col_expr.table or "")
        if table_ref:
            real_table = alias_to_table.get(table_ref, table_ref)
            table_cols[real_table].add(col_name)
        elif len(alias_to_table) == 1:
            # Single-table query: unqualified columns resolve unambiguously.
            real_table = next(iter(alias_to_table.values()))
            table_cols[real_table].add(col_name)
        else:
            table_cols["unknown"].add(col_name)

    return [
        {"table": table, "columns": sorted(cols)}
        for table, cols in sorted(table_cols.items())
        if cols
    ]


def lineage_from_sql(sql: str, filter_logic: str = "", dialect: str = "sqlite") -> Lineage:
    """Convenience wrapper: parse `sql` directly into a Lineage object,
    ready to attach to an AMU. Unresolved ("unknown") column references are
    kept as their own step -- not dropped -- so an unqualified reference to
    a sensitive column still counts toward `Lineage.sensitive_columns()`.
    Pass an explicit filter_logic if you need to capture predicate
    semantics sqlglot can't attribute to a table.
    """
    raw_steps = extract_lineage_from_sql(sql, dialect=dialect)
    steps = tuple(
        LineageStep(table=step["table"], columns_used=tuple(step["columns"]))
        for step in raw_steps
    )
    return Lineage(
        steps=steps,
        filter_logic=filter_logic or sql.strip()[:120].replace("\n", " "),
    )


def lineage_summary(steps: List[Dict]) -> str:
    """Human-readable one-line summary of extracted lineage steps, for logging."""
    if not steps:
        return "(no lineage extracted)"
    return " → ".join(f"{s['table']}({', '.join(s['columns'])})" for s in steps)
