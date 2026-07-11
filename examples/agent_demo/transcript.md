# Lineage-Aware Memory Governance — Agent Demo Transcript
*Generated: 2026-07-11 17:54:56*

## Step 1: Finance writes `high_value_segment`
sensitivity_tags = `{'income'}`, definition_hash = `0c14d41b60ba`

## Step 2: Marketing requests `high_value_segment`
Result: **BLOCKED -> Marketing falls back to in-scope recompute**. Conflict with Finance's definition: `True`
(Finance hash `0c14d41b60ba` vs Marketing hash `67843027f138`)

## Step 3: Finance writes `order_volume`
sensitivity_tags = `set()` (empty)

## Step 4: Marketing requests `order_volume`
Result: **SERVED from memory**, value = `$100,500.00`

## Summary
| Step | Metric | Requester | Outcome |
|---|---|---|---|
| 1 | high_value_segment | — | Finance writes (income-derived) |
| 2 | high_value_segment | Marketing | BLOCKED -> Marketing falls back to in-scope recompute |
| 3 | order_volume | — | Finance writes (no sensitive columns) |
| 4 | order_volume | Marketing | served from memory |