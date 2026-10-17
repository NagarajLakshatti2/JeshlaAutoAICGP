from csv_search import search_csv, format_csv_results


questions = [
    "Which people know Playwright?",
    "Who has more than 8 years of experience?",
    "Who has exactly 8 years of experience?",
    "Who has less than 8 years of experience?",
    "Who worked on Wells Fargo?"
]


for question in questions:

    print("\n" + "=" * 70)
    print("QUESTION:", question)
    print("=" * 70)

    results = search_csv(question)

    print(format_csv_results(results))