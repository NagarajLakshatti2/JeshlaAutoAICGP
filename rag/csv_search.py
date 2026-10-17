import csv
from pathlib import Path

from xlsx_search import load_xlsx_files
from structured_search import structured_search
from dataset_registry import group_datasets


DATA_FOLDER = Path("data")


def load_csv_files():

    rows = []

    csv_files = list(DATA_FOLDER.glob("*.csv"))

    for csv_path in csv_files:

        with open(
            csv_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row_number, row in enumerate(
                reader,
                start=2
            ):

                row["_source"] = csv_path.name
                row["_file_type"] = "csv"
                row["_sheet"] = ""
                row["_page"] = row_number

                rows.append(row)

    return rows


def load_structured_data():
    csv_rows = load_csv_files()
    xlsx_rows = load_xlsx_files()

    return csv_rows + xlsx_rows


def search_csv(query):

    rows = load_structured_data()

    return structured_search(
        query,
        rows
    )


def format_csv_results(results):

    if not results:
        return "No matching structured records found."

    output = []

    for row in results:

        output.append(
            f"Name: {row.get('Name', '')}\n"
            f"Role: {row.get('Role', '')}\n"
            f"Experience: {row.get('Experience', '')} years\n"
            f"Skills: {row.get('Skills', '')}\n"
            f"Project: {row.get('Project', '')}\n"
            f"Source: {row.get('_source', '')}\n"
            f"File Type: {row.get('_file_type', 'xlsx' if row.get('_sheet') else 'csv')}\n"
            f"Sheet: {row.get('_sheet', '')}\n"
            f"Row: {row.get('_page', '')}"
        )

    return "\n\n".join(output)

def get_structured_datasets():

    rows = load_structured_data()

    datasets = group_datasets(rows)

    return datasets