
from pathlib import Path
import csv
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
input_file = ROOT / "outputs" / "fertilizer_cleaned.csv"


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


counts = Counter()
areas = []
unique_households = set()

with input_file.open(
    "r", newline="", encoding="utf-8-sig"
) as file:
    reader = csv.DictReader(file)

    required = {
        "quantity_kg",
        "conversion_status",
        "Parent_ID",
        "HH_ID",
        "Plot_area_kh",
    }

    missing = required - set(reader.fieldnames or [])

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    for row in reader:
        counts["total_records"] += 1

        quantity = number(row["quantity_kg"])
        area = number(row["Plot_area_kh"])

        converted = row["conversion_status"] == "converted"
        has_ids = bool(row["Parent_ID"] and row["HH_ID"])
        valid_area = area is not None and area > 0

        if converted and quantity is not None and quantity >= 0:
            counts["valid_quantities"] += 1

        if has_ids:
            counts["records_with_ids"] += 1
            unique_households.add(row["HH_ID"])

        if valid_area:
            counts["positive_area_records"] += 1
            areas.append(area)

        if converted and quantity is not None and has_ids and valid_area:
            counts["records_ready_for_area_analysis"] += 1


print("\nFERTILIZER DATA AUDIT")
for name, value in sorted(counts.items()):
    print(f"{name}: {value}")

print("Unique household IDs:", len(unique_households))

if areas:
    areas.sort()
    print("Minimum recorded area:", areas[0])
    print("Median recorded area:", areas[len(areas) // 2])
    print("Maximum recorded area:", areas[-1])

print("\nNote: Plot area units must be verified before rate calculation.")
