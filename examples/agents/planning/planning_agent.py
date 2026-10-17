# ============================================
# PRACTICAL PLANNING AGENT
# ============================================


# --------------------------------------------
# CREATE INITIAL STATE
# --------------------------------------------

def create_state(goal):

    return {
        "goal": goal,

        "planning": [
            {
                "id": 1,
                "task": "Read Jira requirement",
                "status": "pending"
            },
            {
                "id": 2,
                "task": "Inspect repository",
                "status": "pending"
            },
            {
                "id": 3,
                "task": "Generate missing automation",
                "status": "pending"
            },
            {
                "id": 4,
                "task": "Execute tests",
                "status": "pending"
            },
            {
                "id": 5,
                "task": "Report result",
                "status": "pending"
            }
        ],

        "current_plan_step": 0,

        "missing_components": [],

        "observations": [],

        "errors": [],

        "test_attempt": 0,

        "final_answer": None
    }


# --------------------------------------------
# PRINT PLAN
# --------------------------------------------

def print_plan(state):

    print("\nCurrent Plan:")

    for step in state["planning"]:

        print(
            f'{step["id"]}. '
            f'{step["task"]} '
            f'[{step["status"].upper()}]'
        )


# --------------------------------------------
# TOOLS
# --------------------------------------------

def get_jira_issue():

    return {
        "issue_key": "QAP-100",
        "requirement": "Automate email validation"
    }


def inspect_repository():

    return {
        "feature": True,
        "step_definition": False,
        "page_object": True
    }


def generate_component(component):

    return f"{component} generated successfully"


def run_tests(state):

    state["test_attempt"] += 1

    # Simulate failure on first execution
    if state["test_attempt"] == 1:

        return {
            "status": "failed",
            "error": "Compilation error: missing import"
        }

    # Second execution succeeds
    return {
        "status": "passed",
        "message": "All tests passed"
    }


def analyze_failure():

    return {
        "root_cause": "Generated Step Definition is missing an import",
        "fix": "Add required Page Object import"
    }


def fix_code():

    return "Missing import added successfully"


# --------------------------------------------
# REPLANNING
# --------------------------------------------

def replan_after_test_failure(state):

    print("\n🔄 Replanning because test execution failed...")

    # Report step will be moved after recovery steps.
    for step in state["planning"]:

        if step["task"] == "Report result":
            step["status"] = "skipped"

    next_id = max(
        step["id"] for step in state["planning"]
    ) + 1

    new_steps = [
        {
            "id": next_id,
            "task": "Analyze test failure",
            "status": "pending"
        },
        {
            "id": next_id + 1,
            "task": "Fix generated code",
            "status": "pending"
        },
        {
            "id": next_id + 2,
            "task": "Re-run tests",
            "status": "pending"
        },
        {
            "id": next_id + 3,
            "task": "Report final result",
            "status": "pending"
        }
    ]

    state["planning"].extend(new_steps)


# --------------------------------------------
# EXECUTE PLAN STEP
# --------------------------------------------

def execute_step(state, step):

    task = step["task"]

    print(f"\n▶ Executing: {task}")

    step["status"] = "in_progress"

    # ----------------------------------------
    # STEP 1 - JIRA
    # ----------------------------------------

    if task == "Read Jira requirement":

        result = get_jira_issue()

        state["observations"].append(result)

        print("Observation:", result)

        step["status"] = "completed"


    # ----------------------------------------
    # STEP 2 - REPOSITORY
    # ----------------------------------------

    elif task == "Inspect repository":

        result = inspect_repository()

        state["observations"].append(result)

        print("Observation:", result)

        if not result["feature"]:
            state["missing_components"].append(
                "feature"
            )

        if not result["step_definition"]:
            state["missing_components"].append(
                "step_definition"
            )

        if not result["page_object"]:
            state["missing_components"].append(
                "page_object"
            )

        print(
            "Missing components:",
            state["missing_components"]
        )

        step["status"] = "completed"


    # ----------------------------------------
    # STEP 3 - GENERATION
    # ----------------------------------------

    elif task == "Generate missing automation":

        if not state["missing_components"]:

            print(
                "Nothing missing. "
                "Generation skipped."
            )

            step["status"] = "skipped"

            return

        for component in state["missing_components"]:

            result = generate_component(
                component
            )

            print("Observation:", result)

            state["observations"].append(
                result
            )

        state["missing_components"] = []

        step["status"] = "completed"


    # ----------------------------------------
    # STEP 4 - TEST
    # ----------------------------------------

    elif task == "Execute tests":

        result = run_tests(state)

        print("Observation:", result)

        state["observations"].append(result)

        if result["status"] == "passed":

            step["status"] = "completed"

        else:

            step["status"] = "failed"

            state["errors"].append(
                result["error"]
            )

            replan_after_test_failure(
                state
            )


    # ----------------------------------------
    # ANALYZE FAILURE
    # ----------------------------------------

    elif task == "Analyze test failure":

        result = analyze_failure()

        print("Observation:", result)

        state["observations"].append(result)

        step["status"] = "completed"


    # ----------------------------------------
    # FIX
    # ----------------------------------------

    elif task == "Fix generated code":

        result = fix_code()

        print("Observation:", result)

        state["observations"].append(result)

        step["status"] = "completed"


    # ----------------------------------------
    # RE-RUN
    # ----------------------------------------

    elif task == "Re-run tests":

        result = run_tests(state)

        print("Observation:", result)

        state["observations"].append(result)

        if result["status"] == "passed":

            step["status"] = "completed"

        else:

            step["status"] = "failed"


    # ----------------------------------------
    # REPORT
    # ----------------------------------------

    elif task == "Report result":

        step["status"] = "completed"


    elif task == "Report final result":

        state["final_answer"] = (
            "Automation completed and "
            "tests passed successfully."
        )

        step["status"] = "completed"


# --------------------------------------------
# PLANNING AGENT
# --------------------------------------------

def run_planning_agent(goal):

    state = create_state(goal)

    print("\nGOAL:", state["goal"])

    print_plan(state)

    index = 0

    while index < len(state["planning"]):

        step = state["planning"][index]

        state["current_plan_step"] = (
            step["id"]
        )

        if step["status"] == "pending":

            execute_step(
                state,
                step
            )

        index += 1

    print_plan(state)

    return state


# --------------------------------------------
# START
# --------------------------------------------

if __name__ == "__main__":

    result = run_planning_agent(
        "Automate QAP-100"
    )

    print(
        "\n========== FINAL ANSWER =========="
    )

    print(
        result["final_answer"]
    )