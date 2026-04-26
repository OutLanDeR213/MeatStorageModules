# Architectural Design

## Key constraint

Direct modification of `product.product` or `product.template` is forbidden.

## Solution: `stock.valuation.layer` with `quantity=0`

Instead of touching the product cost, we create a new `stock.valuation.layer` record with:
- `quantity = 0` — no physical stock change
- `value = storage_cost` — cost adjustment only

This is the standard Odoo pattern used by **Landed Costs** and inventory revaluations.
It increases the product's inventory value on the balance sheet without modifying `standard_price`.

## Why a separate log model (`stock.storage.cost`)?

`stock.valuation.layer` does not store context needed for the report:
- Which layer was the original receipt (initial cost)
- How many times this specific batch was adjusted (adjustment number)
- The weight in kg at the time of accrual

A dedicated log table gives full traceability and makes the report query simple and fast.

## Why `_auto = False` for the report?

The report aggregates data across two tables (`stock_storage_cost` + `stock_valuation_layer`).
A SQL view is more efficient than computed fields, and works natively with Odoo's pivot view.

## UoM handling

Two cases are supported:
- **Weight UoM (kg, g, t)** — converted to kg via `uom._compute_quantity()`
- **Piece/other UoM** — multiplied by `product.weight` (weight per unit in kg)

## Protection against double-run

At the start of `_compute_daily_storage_costs()` we check if a record for today already exists.
If yes — skip. This prevents double accrual if cron runs twice (e.g., after server restart).

## Rate

`0.01 USD/kg/day` is hardcoded as a constant.
For production use it can be moved to `res.config.settings` as a company-level parameter.
