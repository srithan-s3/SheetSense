"""Generate deterministic, entirely synthetic demonstration datasets.

Run with backend/.venv/Scripts/python.exe scripts/generate_samples.py on Windows.
No external data or real people are used. CSV files need only the standard library;
the multi-sheet workbook additionally uses openpyxl from backend requirements.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "sample_data"


def write_csv(name, headers, rows):
    with (ROOT / f"synthetic_{name}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def generate():
    ROOT.mkdir(exist_ok=True)
    rng = random.Random(42)
    products = [("Desk lamp", "Home", 49), ("Headphones", "Electronics", 129),
                ("Notebook", "Stationery", 12), ("Backpack", "Accessories", 65),
                ("Keyboard", "Electronics", 89), ("Water bottle", "Accessories", 24)]
    sales = []
    for i in range(240):
        product, category, price = rng.choice(products)
        units = rng.randint(1, 12)
        sales.append([f"ORD-{i + 1:04d}", (date(2025, 1, 1) + timedelta(days=i * 3 // 4)).isoformat(),
                      product, category, rng.choice(["North", "South", "East", "West"]), units,
                      round(price * units * rng.uniform(.88, 1.03), 2)])
    write_csv("sales", ["Order ID", "Date", "Product", "Category", "Region", "Units", "Revenue"], sales)

    students = []
    for i in range(80):
        base = rng.randint(45, 87)
        students.append([f"STU-{i + 1:03d}", f"Synthetic student {i + 1:02d}", rng.choice(["Section A", "Section B", "Section C"]),
                         min(100, max(0, base + rng.randint(-15, 15))), min(100, max(0, base + rng.randint(-15, 15))),
                         min(100, max(0, base + rng.randint(-15, 15))), rng.randint(65, 100)])
    student_headers = ["Student ID", "Student", "Section", "Mathematics", "Science", "English", "Attendance percent"]
    write_csv("students", student_headers, students)

    expenses = [[f"EXP-{i + 1:03d}", rng.choice(["Groceries", "Transport", "Dining", "Utilities", "Learning"]),
                 rng.choice(["Card", "Cash", "Bank transfer"]), round(rng.uniform(8, 230), 2)] for i in range(120)]
    write_csv("expenses", ["Expense ID", "Category", "Payment method", "Amount"], expenses)

    inventory = []
    for i in range(45):
        inventory.append([f"SKU-{i + 1:03d}", f"Synthetic item {i + 1:02d}", rng.choice(["Electronics", "Home", "Stationery"]),
                          rng.choice(["Warehouse A", "Warehouse B"]), rng.randint(0, 260), rng.randint(10, 60), round(rng.uniform(4, 150), 2)])
    write_csv("inventory", ["SKU", "Item", "Category", "Warehouse", "Stock", "Reorder level", "Unit cost"], inventory)

    try:
        from openpyxl import Workbook
    except ImportError:
        print("Generated four CSVs. Install backend requirements and rerun for the Excel workbook.")
        return
    workbook = Workbook()
    term1 = workbook.active
    term1.title = "Term 1"
    term1.append(student_headers)
    for row in students:
        term1.append(row)
    term2 = workbook.create_sheet("Term 2")
    term2.append(student_headers)
    for row in students:
        term2.append(row[:3] + [min(100, max(0, score + rng.randint(-8, 12))) for score in row[3:]])
    workbook.properties.title = "Synthetic student performance — demonstration only"
    workbook.properties.description = "Programmatically generated fictional records. No real student data."
    workbook.save(ROOT / "synthetic_student_workbook.xlsx")
    print("Generated four synthetic CSV datasets and one two-sheet Excel workbook.")


if __name__ == "__main__":
    generate()
