from csv_search import get_structured_datasets


datasets = get_structured_datasets()


print("\n" + "=" * 70)
print("DATASET / SCHEMA DETECTION")
print("=" * 70)


for dataset_type, rows in datasets.items():

    print(f"\nDataset Type: {dataset_type}")
    print(f"Rows: {len(rows)}")

    if rows:

        print("Source:", rows[0].get("_source"))

        columns = [
            key
            for key in rows[0].keys()
            if not key.startswith("_")
        ]

        print("Columns:", columns)