# Buy or Wait? — AI-Powered Financial Decision Agent

## Overview
A deterministic Python engine that evaluates financial requests and recommends whether to pay in full, partially, via installments, wait, or not proceed. It reconstructs a user's financial position from structured profiles, transaction history, exchange rates, and supporting evidence (messages, receipts) to make safe, personalized payment recommendations.

## Features
- **90-day cash flow forecasting** with category-level recurring expense detection
- **Binary-search safe amount calculator** ensuring balance never drops below user-defined minimum
- **Multi-method payment evaluation** — full payment, installments, partial payment, wait
- **Spending change analysis** — identifies flexible expenses that can be stopped or reduced
- **Multi-format data processing** — CSVs, receipt/invoice images, natural language messages
- **Currency conversion** with fixed exchange rates and multi-hop chaining

## Requirements
- Python 3.8+ (standard library only — no external dependencies)

## How to Run

### 1. Interactive Web Application (Streamlit)
```bash
pip install -r requirements.txt
streamlit run app.py
```
This opens the interactive web dashboard where you can inspect user profiles, simulate 90-day cash flow projections, and test purchase affordability decisions in real-time.

### 2. Batch Processing CLI
```bash
python code/main.py
```
This will:
1. Load all dataset files from `dataset/`
2. Process all financial requests
3. Write results to `dataset/output.csv`

## Architecture

### Pipeline

```
CSV Data + Images → Data Loader → Message Processor → Recurring Detector
    → 90-Day Forecast → Safe Amount Calculator → Payment Plan Evaluator
    → Spending Change Analyzer → output.csv
```

### Data Loading
- Loads all CSVs from `dataset/`
- Applies image amounts (extracted from 16 PNG receipts/invoices)
- Builds lookup indices for users, events, payment options, messages

### Message Processing
- Extracts financial adjustments from user messages:
  - Pending refunds/prizes/payouts (excluded from available funds)
  - Employment status changes
  - Rent increases
  - Unrealized investment gains (excluded)

### Recurring Detection
- Groups all settled events by (category, direction)
- Computes median monthly totals from last 6 months of history
- Detects salary timing (typical day-of-month)

### 90-Day Forecast
- Gap-fill approach: explicit future events + projected recurring patterns
- For each month, if explicit events cover a category, no projection is added
- Otherwise, prorated monthly pattern is projected
- Handles rent increases, employment endings

### Decision Engine
1. Calculates maximum safe amount via binary search
2. Finds earliest full payment date
3. Evaluates all payment options (full, installments, partial, wait)
4. Attempts spending changes if no direct solution found
5. Ranks plans by: completion by deadline → no changes → lowest cost → earliest start → fewest payments

### Output Schema
```
request_id, amount_safe_to_pay, affordability_status, recommended_payment_method,
payment_plan, earliest_date_for_full_payment, spending_changes_needed, decision_explanation
```

## Project Structure
```
├── code/
│   ├── main.py          # Core financial decision engine
│   └── validate.py      # Validation against sample requests
├── dataset/
│   ├── financial_profiles.csv
│   ├── financial_events.csv
│   ├── exchange_rates.csv
│   ├── requests.csv
│   ├── request_payment_options.csv
│   ├── messages.csv
│   ├── images.csv
│   ├── output.csv       # Generated output
│   └── media/images/    # Receipt & invoice images
├── evaluation/
│   └── usage_report.md
└── README.md
```

## Key Design Decisions
- **Deterministic engine** — same input always gives same output, no LLM dependency
- **Category-level aggregation** — avoids double-counting when users have multiple events per category
- **Conservative forecasting** — pending credits not counted until settled, minimum balance enforced at every point in the forecast window
- **Gap-fill approach** — only projects recurring patterns where explicit future events don't already exist
