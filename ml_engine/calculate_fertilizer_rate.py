
from pathlib import Path
import csv
from collections import Counter
from statistics import median

ROOT = Path(__file__).resolve().parent.parent

input_file = ROOT / "outputs" / "fertilizer_cleaned.csv"
output_file = ROOT / "outputs" / "fertilizer_rate_review.csv"


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


counts = Counter()
rates = []

with input_file.open(
    "r", newline="", encoding="utf-8-sig"
) as source:

    reader = csv.DictReader(source)
    headers = reader.fieldnames or []

    required = {
        "quantity_kg",
        "conversion_status",
        "Plot_area_kh",
        "Parent_ID",
        "HH_ID",
    }

    missing = required - set(headers)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    output_headers = headers + [
        "fertilizer_rate_kg_per_recorded_area_unit",
        "rate_status",
    ]

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open(
        "w", newline="", encoding="utf-8-sig"
    ) as target:

        writer = csv.DictWriter(
            target, fieldnames=output_headers
        )
        writer.writeheader()

        for row in reader:
            quantity = to_number(row["quantity_kg"])
            area = to_number(row["Plot_area_kh"])

            rate = ""
            status = "invalid_quantity_or_area"

            if row["conversion_status"] != "converted":
                status = "quantity_not_converted"
            elif quantity is None or quantity < 0:
                status = "invalid_quantity"
            elif area is None or area <= 0:
                status = "invalid_area"
            else:
                rate = quantity / area
                status = "area_unit_needs_confirmation"
                rates.append(rate)

            row["fertilizer_rate_kg_per_recorded_area_unit"] = rate
            row["rate_status"] = status

            writer.writerow(row)
            counts[status] += 1

print("\nFERTILIZER RATE REVIEW")
print("Records:", sum(counts.values()))

for status, count in sorted(counts.items()):
    print(f"{status}: {count}")

if rates:
    print("Median provisional rate:", round(median(rates), 4))
    print("Minimum provisional rate:", round(min(rates), 4))
    print("Maximum provisional rate:", round(max(rates), 4))

print("Saved to:", output_file)
print("These rates are NOT confirmed as kg/hectare.")

