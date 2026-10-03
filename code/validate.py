#!/usr/bin/env python3
"""Validate output against sample_requests.csv."""

import csv
import os
import sys

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")

def load_csv(filename):
    path = os.path.join(DATASET_DIR, filename)
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {k.strip(): v.strip() for k, v in row.items()}
            rows.append(cleaned)
    return rows

def main():
    samples = load_csv("sample_requests.csv")
    
    # Build sample lookup
    expected = {}
    for s in samples:
        expected[s["request_id"]] = s
    
    # Process samples through our engine
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from main import load_all_data, solve as solve_request
    
    data = load_all_data()
    
    # Rebuild sample requests for processing
    sample_requests_raw = []
    for s in samples:
        sample_requests_raw.append({
            "request_id": s["request_id"],
            "user_id": s["user_id"],
            "request_date": s["request_date"],
            "request_type": s["request_type"],
            "requested_amount": s["requested_amount"],
            "desired_completion_date": s["desired_completion_date"],
            "allows_partial_payment": s["allows_partial_payment"],
            "request_text": s["request_text"],
        })
    
    print("=" * 100)
    print("VALIDATION AGAINST 25 SAMPLE REQUESTS")
    print("=" * 100)
    
    correct_status = 0
    correct_method = 0
    correct_safe_amt = 0
    correct_earliest = 0
    total = len(sample_requests_raw)
    
    for req in sample_requests_raw:
        rid = req["request_id"]
        exp = expected[rid]
        
        result = solve_request(data, req)
        
        # Compare
        status_match = result["affordability_status"] == exp["affordability_status"]
        method_match = result["recommended_payment_method"] == exp["recommended_payment_method"]
        
        # Safe amount comparison (within 5% tolerance)
        exp_safe = float(exp.get("amount_safe_to_pay", "0") or "0")
        our_safe = float(result.get("amount_safe_to_pay", "0") or "0")
        if exp_safe > 0:
            safe_pct = abs(our_safe - exp_safe) / exp_safe * 100
        else:
            safe_pct = abs(our_safe - exp_safe) * 100
        safe_match = safe_pct < 10  # within 10%
        
        earliest_match = result.get("earliest_date_for_full_payment", "") == exp.get("earliest_date_for_full_payment", "")
        
        if status_match:
            correct_status += 1
        if method_match:
            correct_method += 1
        if safe_match:
            correct_safe_amt += 1
        if earliest_match:
            correct_earliest += 1
        
        if not (status_match and method_match):
            print(f"\n--- {rid} ---")
            print(f"  Status:   OURS={result['affordability_status']:25s}  EXPECTED={exp['affordability_status']}")
            print(f"  Method:   OURS={result['recommended_payment_method']:25s}  EXPECTED={exp['recommended_payment_method']}")
            print(f"  SafeAmt:  OURS={result['amount_safe_to_pay']:25s}  EXPECTED={exp['amount_safe_to_pay']}")
            print(f"  Earliest: OURS={result.get('earliest_date_for_full_payment',''):25s}  EXPECTED={exp.get('earliest_date_for_full_payment','')}")
            print(f"  Plan:     OURS={result['payment_plan'][:60]}")
            print(f"            EXPT={exp['payment_plan'][:60]}")
            print(f"  Changes:  OURS={result['spending_changes_needed']}")
            print(f"            EXPT={exp['spending_changes_needed']}")
    
    print(f"\n{'=' * 100}")
    print(f"RESULTS: {total} samples")
    print(f"  Status correct:     {correct_status}/{total} ({correct_status/total*100:.1f}%)")
    print(f"  Method correct:     {correct_method}/{total} ({correct_method/total*100:.1f}%)")
    print(f"  Safe amt (±10%):    {correct_safe_amt}/{total} ({correct_safe_amt/total*100:.1f}%)")
    print(f"  Earliest correct:   {correct_earliest}/{total} ({correct_earliest/total*100:.1f}%)")
    print(f"{'=' * 100}")

if __name__ == "__main__":
    main()
