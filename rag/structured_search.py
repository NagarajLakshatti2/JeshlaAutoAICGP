import re


def normalize(text):
    return str(text).strip().lower()


def filter_by_skill(rows, skill):

    results = []

    for row in rows:

        skills = normalize(row.get("Skills", ""))

        if skill in skills:
            results.append(row)

    return results


def filter_by_experience(rows, operator, value):

    results = []

    for row in rows:

        experience_value = row.get("Experience")

        if experience_value in (None, ""):
            continue

        try:
            experience = float(experience_value)
        except (ValueError, TypeError):
            continue

        if operator == ">" and experience > value:
            results.append(row)

        elif operator == "<" and experience < value:
            results.append(row)

        elif operator == "==" and experience == value:
            results.append(row)

        elif operator == ">=" and experience >= value:
            results.append(row)

        elif operator == "<=" and experience <= value:
            results.append(row)

    return results


def filter_by_role(rows, role):

    results = []

    for row in rows:

        row_role = normalize(
            row.get("Role", "")
        )

        if role in row_role:
            results.append(row)

    return results


def filter_by_project(rows, project):

    results = []

    for row in rows:

        row_project = normalize(
            row.get("Project", "")
        )

        if project in row_project:
            results.append(row)

    return results


def structured_search(query, rows):

    query_lower = normalize(query)

    results = rows.copy()

    # =========================================================
    # EXPERIENCE
    # =========================================================

    match = re.search(
        r"(?:more than|greater than|above|over)\s+(\d+)",
        query_lower
    )

    if match:

        value = int(match.group(1))

        results = filter_by_experience(
            results,
            ">",
            value
        )

    else:

        match = re.search(
            r"(?:less than|lower than|below|under)\s+(\d+)",
            query_lower
        )

        if match:

            value = int(match.group(1))

            results = filter_by_experience(
                results,
                "<",
                value
            )

        else:

            match = re.search(
                r"(?:exactly|equal to)\s+(\d+)",
                query_lower
            )

            if match:

                value = int(match.group(1))

                results = filter_by_experience(
                    results,
                    "==",
                    value
                )

    # =========================================================
    # SKILLS
    # =========================================================

    skills = [
        "playwright",
        "selenium",
        "appium",
        "java",
        "python",
        "cucumber",
        "rest assured",
        "api testing"
    ]

    for skill in skills:

        if skill in query_lower:

            results = filter_by_skill(
                results,
                skill
            )

    # =========================================================
    # ROLES
    # =========================================================

    roles = [
        "qa engineer",
        "qa lead",
        "automation engineer",
        "sdet"
    ]

    for role in roles:

        if role in query_lower:

            results = filter_by_role(
                results,
                role
            )

            break

    # =========================================================
    # PROJECTS
    # =========================================================

    projects = [
        "wells fargo",
        "banking",
        "healthcare",
        "fintech",
        "e-commerce"
    ]

    for project in projects:

        if project in query_lower:

            results = filter_by_project(
                results,
                project
            )

            break

    return results