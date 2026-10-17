from xlsx_search import load_xlsx_files


rows = load_xlsx_files()

print("\n" + "=" * 70)
print("XLSX RECORDS")
print("=" * 70)

print(f"Total XLSX rows: {len(rows)}")

for row in rows:

    print("\n------------------------------")

    print("Name:", row.get("Name"))
    print("Role:", row.get("Role"))
    print("Experience:", row.get("Experience"))
    print("Skills:", row.get("Skills"))
    print("Project:", row.get("Project"))
    print("Source:", row.get("_source"))
    print("Sheet:", row.get("_sheet"))
    print("Row:", row.get("_page"))