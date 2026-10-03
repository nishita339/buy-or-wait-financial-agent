from __future__ import annotations

import csv
import sys

from decimal import Decimal, InvalidOperation
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATASET = ROOT / "dataset"

OUTPUT = ROOT / "output.csv"


# ============================================================
# REQUIRED OUTPUT COLUMNS
# ============================================================

REQUIRED_COLUMNS = [

    "request_id",

    "amount_safe_to_pay",

    "affordability_status",

    "recommended_payment_method",

    "payment_plan",

    "earliest_date_for_full_payment",

    "spending_changes_needed",

    "decision_explanation",

]


# ============================================================
# VALID STATUS VALUES
# ============================================================

VALID_AFFORDABILITY_STATUS = {

    "affordable",

    "partially_affordable",

    "not_affordable",

}


# ============================================================
# CSV READER
# ============================================================

def read_csv(path: Path):
    """
    Read CSV file and return a list of dictionaries.
    """

    if not path.exists():

        print()

        print(
            f"ERROR: File not found: {path}"
        )

        sys.exit(1)


    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        return list(
            csv.DictReader(file)
        )


# ============================================================
# SAFE DECIMAL CONVERSION
# ============================================================

def amount(value):
    """
    Convert a value into Decimal safely.

    Examples:

        100
        100.50
        ₹1,000
        1,000.00

    Empty values become 0.
    """

    if value is None:
        return Decimal("0")


    text = str(
        value
    ).strip()


    if not text:
        return Decimal("0")


    # Remove commas.

    text = text.replace(
        ",",
        "",
    )


    # Remove common currency symbols.

    for symbol in [

        "₹",

        "$",

        "€",

        "£",

    ]:

        text = text.replace(
            symbol,
            "",
        )


    try:

        return Decimal(
            text
        )


    except (
        InvalidOperation,
        ValueError,
    ):

        return Decimal("0")


# ============================================================
# CHECK OUTPUT FILE EXISTS
# ============================================================

def check_output_exists():
    """
    Check whether output.csv exists.
    """

    if not OUTPUT.exists():

        print()

        print("=" * 60)

        print("ERROR: output.csv NOT FOUND")

        print("=" * 60)

        print()

        print(
            "Please run:"
        )

        print()

        print(
            "python3 code/main.py"
        )

        print()

        sys.exit(1)


# ============================================================
# VALIDATE OUTPUT COLUMNS
# ============================================================

def validate_columns(output_rows):
    """
    Validate output.csv schema.
    """

    print(
        "Checking output columns..."
    )


    if not output_rows:

        raise AssertionError(
            "output.csv is empty."
        )


    actual_columns = list(
        output_rows[0].keys()
    )


    # --------------------------------------------------------
    # Check Exact Columns
    # --------------------------------------------------------

    if actual_columns != REQUIRED_COLUMNS:

        print()

        print(
            "Expected columns:"
        )

        for column in REQUIRED_COLUMNS:

            print(
                f"  - {column}"
            )


        print()

        print(
            "Actual columns:"
        )

        for column in actual_columns:

            print(
                f"  - {column}"
            )


        raise AssertionError(
            "Output columns do not match "
            "the required schema."
        )


    print(
        "✓ Output columns are correct."
    )


# ============================================================
# VALIDATE ROW COUNT
# ============================================================

def validate_row_count(
    requests,
    output_rows,
):
    """
    Validate exactly one output row
    for every request.
    """

    print(
        "Checking row count..."
    )


    request_count = len(
        requests
    )


    output_count = len(
        output_rows
    )


    if request_count != output_count:

        raise AssertionError(

            f"Row count mismatch: "

            f"{request_count} requests "

            f"but {output_count} output rows."

        )


    print(
        "✓ Exactly one output row "
        "per request."
    )


# ============================================================
# VALIDATE REQUEST IDS
# ============================================================

def validate_request_ids(
    requests,
    output_rows,
):
    """
    Validate that all request IDs
    are present exactly once.
    """

    print(
        "Checking request IDs..."
    )


    request_ids = [

        row["request_id"]

        for row in requests

    ]


    output_ids = [

        row["request_id"]

        for row in output_rows

    ]


    # --------------------------------------------------------
    # Check Duplicate IDs
    # --------------------------------------------------------

    duplicate_ids = set()


    seen = set()


    for request_id in output_ids:

        if request_id in seen:

            duplicate_ids.add(
                request_id
            )


        seen.add(
            request_id
        )


    if duplicate_ids:

        raise AssertionError(

            "Duplicate request IDs found: "

            f"{sorted(duplicate_ids)}"

        )


    # --------------------------------------------------------
    # Check Missing IDs
    # --------------------------------------------------------

    missing_ids = (

        set(request_ids)

        -

        set(output_ids)

    )


    if missing_ids:

        raise AssertionError(

            "Missing request IDs: "

            f"{sorted(missing_ids)}"

        )


    # --------------------------------------------------------
    # Check Extra IDs
    # --------------------------------------------------------

    extra_ids = (

        set(output_ids)

        -

        set(request_ids)

    )


    if extra_ids:

        raise AssertionError(

            "Unexpected request IDs: "

            f"{sorted(extra_ids)}"

        )


    print(
        "✓ All request IDs are correct."
    )


# ============================================================
# VALIDATE SAFE AMOUNT
# ============================================================

def validate_amount_bounds(
    requests,
    output_rows,
):
    """
    Validate:

        amount_safe_to_pay >= 0

        amount_safe_to_pay <= requested_amount
    """

    print(
        "Checking amount bounds..."
    )


    output_by_id = {

        row["request_id"]: row

        for row in output_rows

    }


    errors = []


    for request in requests:


        request_id = request[
            "request_id"
        ]


        output = output_by_id[
            request_id
        ]


        safe_amount = amount(

            output.get(
                "amount_safe_to_pay"
            )

        )


        requested_amount = amount(

            request.get(
                "requested_amount"
            )

        )


        # ----------------------------------------------------
        # Check Negative
        # ----------------------------------------------------

        if safe_amount < 0:

            errors.append(

                f"{request_id}: "

                f"amount_safe_to_pay is negative "

                f"({safe_amount})"

            )


        # ----------------------------------------------------
        # Check Maximum
        # ----------------------------------------------------

        if safe_amount > requested_amount:

            errors.append(

                f"{request_id}: "

                f"safe amount {safe_amount} "

                f"exceeds requested amount "

                f"{requested_amount}"

            )


    if errors:

        print()

        print(
            "Amount validation errors:"
        )

        print()


        for error in errors[:20]:

            print(
                f"  ✗ {error}"
            )


        if len(errors) > 20:

            print()

            print(
                f"... and "
                f"{len(errors) - 20} more errors"
            )


        raise AssertionError(
            "Amount bounds validation failed."
        )


    print(
        "✓ All safe amounts are within valid bounds."
    )


# ============================================================
# VALIDATE AFFORDABILITY STATUS
# ============================================================

def validate_affordability_status(
    output_rows,
):
    """
    Validate affordability_status values.
    """

    print(
        "Checking affordability status..."
    )


    errors = []


    for row in output_rows:


        request_id = row[
            "request_id"
        ]


        status = str(

            row.get(
                "affordability_status",
                "",
            )

        ).strip()


        if (

            status

            not in

            VALID_AFFORDABILITY_STATUS

        ):

            errors.append(

                f"{request_id}: "

                f"Invalid affordability_status "

                f"'{status}'"

            )


    if errors:

        print()


        for error in errors[:20]:

            print(
                f"  ✗ {error}"
            )


        raise AssertionError(
            "Invalid affordability status found."
        )


    print(
        "✓ All affordability statuses are valid."
    )


# ============================================================
# VALIDATE REQUIRED FIELDS
# ============================================================

def validate_required_fields(
    output_rows,
):
    """
    Validate that every output row
    contains all required fields.
    """

    print(
        "Checking required fields..."
    )


    errors = []


    for row in output_rows:


        request_id = row.get(
            "request_id",
            "<unknown>",
        )


        for column in REQUIRED_COLUMNS:


            if column not in row:

                errors.append(

                    f"{request_id}: "

                    f"Missing column '{column}'"

                )


    if errors:

        for error in errors[:20]:

            print(
                f"  ✗ {error}"
            )


        raise AssertionError(
            "Required field validation failed."
        )


    print(
        "✓ All required fields exist."
    )


# ============================================================
# COMPARE WITH SAMPLE REQUESTS
# ============================================================

def evaluate_samples(
    samples,
    output_rows,
):
    """
    Compare generated predictions with
    solved sample requests.

    This is informational and does not
    fail the evaluation if accuracy is low.
    """

    print(
        "Evaluating solved samples..."
    )


    if not samples:

        print(
            "⚠ No sample_requests.csv found "
            "or file is empty."
        )

        return


    output_by_id = {

        row["request_id"]: row

        for row in output_rows

    }


    fields_to_check = [

        "amount_safe_to_pay",

        "affordability_status",

        "recommended_payment_method",

        "payment_plan",

        "earliest_date_for_full_payment",

    ]


    checks = 0

    passed = 0


    sample_results = []


    for sample in samples:


        request_id = sample.get(
            "request_id"
        )


        prediction = output_by_id.get(
            request_id
        )


        if not prediction:

            sample_results.append(

                {

                    "request_id": request_id,

                    "status": "MISSING OUTPUT",

                }

            )

            continue


        request_passed = 0

        request_checks = 0


        for field in fields_to_check:


            # Skip if sample does not
            # contain a label.

            if field not in sample:

                continue


            expected = str(

                sample.get(
                    field,
                    "",
                )

            ).strip()


            # Skip blank sample labels.

            if expected == "":
                continue


            predicted = str(

                prediction.get(
                    field,
                    "",
                )

            ).strip()


            checks += 1

            request_checks += 1


            # ------------------------------------------------
            # Special comparison for money
            # ------------------------------------------------

            if field == "amount_safe_to_pay":

                if amount(
                    predicted
                ) == amount(
                    expected
                ):

                    passed += 1

                    request_passed += 1

                continue


            # ------------------------------------------------
            # Normal String Comparison
            # ------------------------------------------------

            if predicted == expected:

                passed += 1

                request_passed += 1


        sample_results.append(

            {

                "request_id": request_id,

                "passed": request_passed,

                "checks": request_checks,

            }

        )


    print(
        "✓ Sample evaluation completed."
    )


    print()

    print(
        f"Sample field accuracy: "
        f"{passed}/{checks}"
    )


    if checks > 0:

        accuracy = (

            passed

            / checks

        ) * 100


        print(
            f"Sample accuracy: "
            f"{accuracy:.2f}%"
        )


# ============================================================
# PRINT DATASET SUMMARY
# ============================================================

def print_summary(
    requests,
    output_rows,
    samples,
):
    """
    Print evaluation summary.
    """

    print()

    print("=" * 60)

    print(
        "EVALUATION SUMMARY"
    )

    print("=" * 60)

    print()

    print(
        f"Requests: {len(requests)}"
    )

    print(
        f"Output rows: {len(output_rows)}"
    )

    print(
        f"Sample requests: {len(samples)}"
    )

    print()

    print(
        "Schema checks: PASSED"
    )

    print(
        "Request ID checks: PASSED"
    )

    print(
        "Amount bounds checks: PASSED"
    )

    print(
        "Affordability status checks: PASSED"
    )

    print()

    print(
        "✓ ALL REQUIRED VALIDATIONS PASSED"
    )

    print()

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print("=" * 60)

    print(
        "FINANCIAL FORECAST ENGINE EVALUATION"
    )

    print("=" * 60)

    print()


    # --------------------------------------------------------
    # Check Output Exists
    # --------------------------------------------------------

    check_output_exists()


    # --------------------------------------------------------
    # Load Dataset
    # --------------------------------------------------------

    print(
        "Loading files..."
    )


    requests = read_csv(

        DATASET

        / "requests.csv"

    )


    output_rows = read_csv(
        OUTPUT
    )


    sample_file = (

        DATASET

        / "sample_requests.csv"

    )


    if sample_file.exists():

        samples = read_csv(
            sample_file
        )

    else:

        samples = []


    print(
        "✓ Files loaded successfully."
    )

    print()


    # --------------------------------------------------------
    # Validation 1
    # --------------------------------------------------------

    validate_columns(
        output_rows
    )


    # --------------------------------------------------------
    # Validation 2
    # --------------------------------------------------------

    validate_required_fields(
        output_rows
    )


    # --------------------------------------------------------
    # Validation 3
    # --------------------------------------------------------

    validate_row_count(

        requests,

        output_rows,

    )


    # --------------------------------------------------------
    # Validation 4
    # --------------------------------------------------------

    validate_request_ids(

        requests,

        output_rows,

    )


    # --------------------------------------------------------
    # Validation 5
    # --------------------------------------------------------

    validate_amount_bounds(

        requests,

        output_rows,

    )


    # --------------------------------------------------------
    # Validation 6
    # --------------------------------------------------------

    validate_affordability_status(
        output_rows
    )


    # --------------------------------------------------------
    # Sample Evaluation
    # --------------------------------------------------------

    print()

    evaluate_samples(

        samples,

        output_rows,

    )


    # --------------------------------------------------------
    # Final Summary
    # --------------------------------------------------------

    print_summary(

        requests,

        output_rows,

        samples,

    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()


    except AssertionError as error:

        print()

        print("=" * 60)

        print(
            "VALIDATION FAILED"
        )

        print("=" * 60)

        print()

        print(
            f"ERROR: {error}"
        )

        print()

        sys.exit(1)


    except Exception as error:

        print()

        print("=" * 60)

        print(
            "UNEXPECTED ERROR"
        )

        print("=" * 60)

        print()

        print(
            f"ERROR: {error}"
        )

        print()

        sys.exit(1)