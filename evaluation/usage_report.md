# Usage Report — Buy or Wait?

## Model Information
- **Provider**: N/A (deterministic Python engine, no LLM API calls)
- **Model**: N/A — Pure algorithmic solution
- **Framework**: Python 3 standard library (csv, datetime, math, re, collections)

## Run Summary
- **Total Requests Processed**: 250
- **Total Model Calls**: 0 (deterministic engine)
- **Input Tokens**: 0
- **Output Tokens**: 0
- **Total Tokens**: 0
- **Average Tokens Per Request**: 0
- **Estimated Total Cost**: $0.00
- **Estimated Per-Request Cost**: $0.00

## Architecture
The solution is a fully deterministic Python engine that:
1. Loads all dataset CSVs and image amounts (extracted from visual inspection)
2. Processes user messages for financial adjustments
3. Detects recurring income/expense patterns via category-level monthly aggregation
4. Forecasts 90-day cash flow using gap-fill approach
5. Binary-searches for maximum safe payment amount
6. Evaluates all payment options and ranks by decision rules
7. Attempts spending changes (stop/reduce flexible expenses) if needed

## Status Distribution
| Status | Count |
|---|---|
| affordable_now | 80 |
| affordable_with_plan | 63 |
| affordable_later | 33 |
| not_affordable | 74 |
| **Total** | **250** |
