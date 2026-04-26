# Meat Storage Daily Cost

Odoo 18 module that implements daily storage cost accrual for cold warehouse inventory using FIFO valuation.

## What it does

- Every day increases the cost of products in the warehouse proportionally to their mass
- Rate: **0.01 USD per 1 kg per day**
- Only considers stock remaining at the time of calculation
- Provides an analytical report (tree + pivot) showing:
  - Number of times price was increased per batch
  - Initial cost at warehouse arrival
  - Current cost after all accruals

## Requirements

- Odoo 18 Community
- Modules: `stock`, `stock_account`
- Products must use **FIFO** costing method (set on product category)

## Installation

1. Copy `meat_storage_cost` folder into your Odoo addons path
2. Add the path to `addons_path` in `odoo.conf`
3. Restart Odoo server
4. Go to **Apps** → search `Meat Storage Daily Cost` → **Install**

## Usage

### Automatic (recommended)
The cron job **"Daily Storage Cost Accrual"** runs automatically every day.

### Manual run
**Settings → Technical → Scheduled Actions → Daily Storage Cost Accrual → Run Manually**

### Reports
**Inventory → Storage Costs → Storage Cost Report** — pivot + tree analysis

**Inventory → Storage Costs → Storage Cost Log** — full list of daily accruals
