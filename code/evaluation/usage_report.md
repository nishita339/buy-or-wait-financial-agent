# Usage Report

**Final run date:** 2026-09-13

## Execution

* **Provider:** None
* **Model:** None
* **Strategy:** Deterministic Python financial forecasting engine
* **Model calls:** 0
* **Input tokens:** 0
* **Output tokens:** 0
* **Total tokens:** 0
* **Average tokens per request:** 0
* **Estimated total cost:** $0.00
* **Estimated cost per request:** $0.00

## Implementation Strategy

The submitted implementation does not call an external language model.

The solution uses a deterministic Python-based financial forecasting engine to process the participant-facing dataset files.

The system performs the following operations:

1. Reads financial profiles and transaction events.
2. Reconstructs the user's financial state.
3. Identifies income and expenses.
4. Detects recurring financial events.
5. Forecasts account balances for 90 days.
6. Calculates the maximum safe payment amount.
7. Evaluates affordability.
8. Tests available payment methods and installment plans.
9. Simulates possible spending changes for flexible recurring expenses.
10. Determines the earliest date for full payment.
11. Generates exactly one output row for each request.
12. Validates output schema and payment amount bounds.
13. Writes the final predictions to `output.csv`.

## Model Usage

No external AI or language model provider is used.

* Provider API calls: 0
* Language model calls: 0
* Input tokens: 0
* Output tokens: 0

## Cost

Because the implementation uses only deterministic Python logic and does not make external model calls:

* **Estimated total cost:** $0.00
* **Estimated cost per request:** $0.00

## Output

The implementation generates:

```text
output.csv
```

The output contains the required fields:

* `request_id`
* `amount_safe_to_pay`
* `affordability_status`
* `recommended_payment_method`
* `payment_plan`
* `earliest_date_for_full_payment`
* `spending_changes_needed`
* `decision_explanation`

## Validation

The evaluation script validates:

* Exactly one output row per request.
* Correct request IDs.
* No duplicate request IDs.
* Required output columns.
* Valid affordability status.
* Non-negative safe payment amounts.
* Safe payment amount does not exceed the requested amount.
* Sample request predictions where solved samples are available.
