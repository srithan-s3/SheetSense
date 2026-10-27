# Synthetic samples

Every record in this folder is fictional, generated using seed `42` by
`python scripts/generate_samples.py`. These are demonstrations, not real-world records.

| File | Purpose |
| --- | --- |
| synthetic_sales.csv | 240 orders, ISO dates, products, categories, regions, units and revenue |
| synthetic_students.csv | 80 fictional students, sections, subject marks and attendance |
| synthetic_expenses.csv | 120 expenses, categories, payment methods and amounts; intentionally no dates |
| synthetic_inventory.csv | 45 fictional SKUs, categories, warehouses, stock and reorder levels |
| synthetic_student_workbook.xlsx | The same student example across two selectable worksheets |

Amounts are generic numeric units, not an assumed currency. The app reads each sample
through the same upload and analytics pipeline as your own files.
