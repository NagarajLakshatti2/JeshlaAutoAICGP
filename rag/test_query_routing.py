from dataset_registry import detect_query_dataset


questions = [

    "Who knows Playwright?",

    "Who has more than 8 years of experience?",

    "What is the status of my AI SDET roadmap?",

    "What tools are in my roadmap?",

    "What is the testing automation architecture?",

    "What are the phases in my automation planning?",

    "What is the difference between Java and Python?",

    "What llm modules are available?",

    "Which free rag api are available?",

    "Which free search api are available?",

    "Which free GPU services are available?",

    "Which models have open source licenses?"
]


print("\n" + "=" * 80)
print("DATASET QUERY ROUTING")
print("=" * 80)


for question in questions:

    dataset = detect_query_dataset(question)

    print(f"\nQuestion: {question}")
    print(f"Dataset : {dataset}")