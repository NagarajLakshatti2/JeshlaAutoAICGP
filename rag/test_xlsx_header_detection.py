from xlsx_search import load_xlsx_files
from dataset_registry import group_datasets


print("\n" + "=" * 80)
print("XLSX HEADER DETECTION TEST")
print("=" * 80)


rows = load_xlsx_files()

print(f"\nTotal XLSX rows: {len(rows)}")


datasets = group_datasets(rows)


print("\n" + "=" * 80)
print("DATASET TYPES")
print("=" * 80)


for dataset_type, dataset_rows in datasets.items():

    print(
        f"\nDataset Type: {dataset_type}"
    )

    print(
        f"Rows: {len(dataset_rows)}"
    )

    if dataset_rows:

        sample = dataset_rows[0]

        print(
            f"Source: {sample.get('_source')}"
        )

        print(
            f"Sheet: {sample.get('_sheet')}"
        )

        print(
            "Columns:"
        )

        print(
            [
                key
                for key in sample.keys()
                if not key.startswith("_")
            ]
        )

