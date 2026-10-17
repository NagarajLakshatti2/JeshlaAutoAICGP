def normalize_columns(row):
    """
    Return normalized column names for a structured row.
    """

    return {
        str(key).strip().lower()
        for key in row.keys()
        if key is not None
        and not str(key).startswith("_")
        and str(key).strip()
    }


def detect_dataset_type(row):
    """
    Detect dataset type based on the actual columns.
    """

    columns = normalize_columns(row)

    # --------------------------------------------------
    # Employee dataset
    # --------------------------------------------------

    employee_columns = {
        "name",
        "role",
        "experience",
        "skills",
        "project"
    }

    if employee_columns.issubset(columns):
        return "employees"


    # --------------------------------------------------
    # AI + SDET Roadmap - All Tools
    # --------------------------------------------------

    roadmap_columns = {
        "#",
        "roadmap",
        "stage / block",
        "level / step type",
        "topic / skill",
        "package / tool",
        "open source?",
        "licence",
        "notes / learning resource",
        "priority",
        "status"
    }

    if roadmap_columns.issubset(columns):
        return "roadmap_tools"


    # --------------------------------------------------
    # AI Testing Automation Plan - Architecture
    # --------------------------------------------------

    architecture_columns = {
        "layer",
        "responsibility",
        "tools"
    }

    if architecture_columns.issubset(columns):
        return "automation_architecture"


    # --------------------------------------------------
    # AI Testing Automation Plan - Phased Plan
    # --------------------------------------------------

    phased_plan_columns = {
        "phase",
        "name",
        "what to build",
        "min weeks",
        "max weeks",
        "done when",
        "start",
        "end",
        "status",
        "notes"
    }

    if phased_plan_columns.issubset(columns):
        return "automation_phased_plan"


    # --------------------------------------------------
    # Java vs Python learning topics
    # --------------------------------------------------

    java_python_columns = {
        "#",
        "category",
        "java topic",
        "python topic",
        "priority",
        "status"
    }

    if java_python_columns.issubset(columns):
        return "java_python_topics"


    # --------------------------------------------------
    # Java vs Python topic-wise learning
    # --------------------------------------------------

    topicwise_columns = {
        "#",
        "category",
        "priority",
        "java topic",
        "java question",
        "java answer / explanation",
        "python topic",
        "python question",
        "python answer / explanation",
        "key difference",
        "status"
    }

    if topicwise_columns.issubset(columns):
        return "java_python_topicwise"


    # --------------------------------------------------
    # llm / rag / Agent modules
    # --------------------------------------------------

    llm_rag_columns = {
        "priority",
        "module",
        "type (llm / rag / agent)",
        "modality (text / image / video / speech)",
        "rag step",
        "category",
        "purpose",
        "open source?",
        "local / api",
        "size",
        "free to use?",
        "llm",
        "rag",
        "agent",
        "other"
    }

    if llm_rag_columns.issubset(columns):
        return "llm_rag_modules"


    # --------------------------------------------------
    # Generative AI
    # --------------------------------------------------

    generative_ai_columns = {
        "priority",
        "modality",
        "category",
        "name",
        "open source / license",
        "free to use?",
        "api?",
        "hardware",
        "notes"
    }

    if generative_ai_columns.issubset(columns):
        return "generative_ai"


    # --------------------------------------------------
    # Free api
    # --------------------------------------------------

    free_api_columns = {
        "priority",
        "provider",
        "free limits",
        "card needed?",
        "best for",
        "free to use?",
        "catch"
    }

    if free_api_columns.issubset(columns):
        return "free_apis"


    # --------------------------------------------------
    # Free rag api
    # --------------------------------------------------

    free_rag_columns = {
        "priority",
        "type",
        "rag step",
        "service",
        "free offer",
        "free to use?",
        "best for",
        "notes / catch"
    }

    if free_rag_columns.issubset(columns):
        return "free_rag_apis"


    # --------------------------------------------------
    # Free Search api
    # --------------------------------------------------

    free_search_columns = {
        "priority",
        "type",
        "service",
        "free offer",
        "free to use?",
        "best for",
        "notes / catch"
    }

    if free_search_columns.issubset(columns):
        return "free_search_apis"


    # --------------------------------------------------
    # Free Compute & Tools
    # --------------------------------------------------

    free_compute_columns = {
        "priority",
        "type",
        "service",
        "what you get",
        "free to use?",
        "best for",
        "notes / catch"
    }

    if free_compute_columns.issubset(columns):
        return "free_compute"


    # --------------------------------------------------
    # Model Licenses
    # --------------------------------------------------

    model_license_columns = {
        "priority",
        "model family",
        "modality",
        "status",
        "license / terms",
        "free to download and run?",
        "check result"
    }

    if model_license_columns.issubset(columns):
        return "model_licenses"


    # --------------------------------------------------
    # Unknown
    # --------------------------------------------------

    return "unknown"


def group_datasets(rows):
    """
    Group rows by detected dataset type.
    """

    datasets = {}

    for row in rows:

        dataset_type = detect_dataset_type(row)

        if dataset_type not in datasets:
            datasets[dataset_type] = []

        datasets[dataset_type].append(row)

    return datasets


def detect_query_dataset(query):
    """
    Detect which structured dataset should be searched
    based on the user's question.
    """

    query_lower = query.lower().strip()

    # ============================================================
    # 1. EMPLOYEES
    # ============================================================

    employee_keywords = [
        "who",
        "which people",
        "employee",
        "employees",
        "person",
        "people",
        "experience",
        "worked on",
        "works on",
        "knows",
        "skills"
    ]

    employee_context = [
        "years",
        "experience",
        "playwright",
        "selenium",
        "appium",
        "java",
        "python",
        "cucumber",
        "rest assured",
        "api testing",
        "wells fargo",
        "banking",
        "healthcare",
        "fintech",
        "e-commerce"
    ]

    if (
        any(word in query_lower for word in employee_keywords)
        and any(word in query_lower for word in employee_context)
    ):
        return "employees"


    # ============================================================
    # 2. AUTOMATION PHASED PLAN
    # ============================================================

    phased_plan_keywords = [
        "phases",
        "phase",
        "phased planning",
        "what to build",
        "done when",
        "start",
        "end"
    ]

    automation_context = [
        "automation planning",
        "testing automation planning",
        "test automation planning",
        "automation phase"
    ]

    if (
        any(word in query_lower for word in phased_plan_keywords)
        and any(word in query_lower for word in automation_context)
    ):
        return "automation_phased_plan"


    # ============================================================
    # 3. AUTOMATION ARCHITECTURE
    # ============================================================

    architecture_keywords = [
        "architecture",
        "layers",
        "responsibility",
        "tools"
    ]

    architecture_context = [
        "automation architecture",
        "testing automation architecture",
        "test automation architecture"
    ]

    if (
        any(word in query_lower for word in architecture_keywords)
        and any(word in query_lower for word in architecture_context)
    ):
        return "automation_architecture"


    # ============================================================
    # 4. ROADMAP
    # ============================================================

    roadmap_keywords = [
        "roadmap",
        "learning roadmap",
        "ai sdet roadmap",
        "roadmap stage",
        "roadmap status",
        "roadmap tools"
    ]

    if any(word in query_lower for word in roadmap_keywords):
        return "roadmap_tools"


    # ============================================================
    # 5. JAVA vs PYTHON TOPIC-WISE
    # ============================================================

    if (
        "java" in query_lower
        and "python" in query_lower
        and (
            "topic-wise" in query_lower
            or "topic wise" in query_lower
            or "question" in query_lower
            or "explanation" in query_lower
            or "answer" in query_lower
        )
    ):
        return "java_python_topicwise"


    # ============================================================
    # 6. JAVA vs PYTHON GENERAL TOPICS
    # ============================================================

    if (
        "java" in query_lower
        and "python" in query_lower
        and (
            "difference" in query_lower
            or "compare" in query_lower
            or "comparison" in query_lower
            or "topic" in query_lower
            or "learning" in query_lower
        )
    ):
        return "java_python_topics"


    # ============================================================
    # 7. FREE rag api
    # ============================================================

    if (
        "rag" in query_lower
        and (
            "api" in query_lower
            or "apis" in query_lower
            or "free" in query_lower
            or "service" in query_lower
        )
    ):
        return "free_rag_apis"


    # ============================================================
    # 8. FREE SEARCH api
    # ============================================================

    if (
        (
            "search" in query_lower
            or "web search" in query_lower
        )
        and (
            "api" in query_lower
            or "apis" in query_lower
            or "free" in query_lower
            or "service" in query_lower
        )
    ):
        return "free_search_apis"


    # ============================================================
    # 9. FREE api
    # ============================================================

    if (
        ("api" in query_lower or "apis" in query_lower)
        and "free" in query_lower
    ):
        return "free_apis"


    # ============================================================
    # 10. llm / rag / AGENT MODULES
    # ============================================================

    llm_rag_keywords = [
        "llm",
        "rag",
        "agent",
        "module",
        "modules",
        "tool calling",
        "function calling"
    ]

    if any(word in query_lower for word in llm_rag_keywords):
        return "llm_rag_modules"


    # ============================================================
    # 11. GENERATIVE AI
    # ============================================================

    generative_keywords = [
        "image generation",
        "image model",
        "video generation",
        "speech",
        "generative ai"
    ]

    if any(word in query_lower for word in generative_keywords):
        return "generative_ai"


    # ============================================================
    # 12. FREE COMPUTE
    # ============================================================

    compute_keywords = [
        "gpu",
        "compute",
        "colab",
        "kaggle",
        "hosting",
        "inference"
    ]

    if any(word in query_lower for word in compute_keywords):
        return "free_compute"


    # ============================================================
    # 13. MODEL LICENSES
    # ============================================================

    license_keywords = [
        "license",
        "licence",
        "open source model",
        "open source models",
        "open models",
        "model license",
        "model licence"
    ]

    if any(word in query_lower for word in license_keywords):
        return "model_licenses"


    # ============================================================
    # 14. UNKNOWN
    # ============================================================

    return None