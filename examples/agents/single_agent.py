# ============================================================
# CLEAN SINGLE AGENT
# ============================================================

MAX_STEPS = 15
MAX_TEST_ATTEMPTS = 3


# ============================================================
# 1. STATE
# ============================================================

def create_state(goal):

    return {
        "goal": goal,

        "status": "running",

        "plan": [],
        "current_plan_step": 0,

        "relevant_memory": [],

        "jira_result": None,
        "repository_result": None,

        "missing_components": [],

        "observations": [],
        "errors": [],

        "step_count": 0,
        "test_attempts": 0,

        "final_answer": None,
        "stop_reason": None
    }


# ============================================================
# 2. MEMORY
# ============================================================

MEMORY_STORE = [
    "Project uses Gradle",
    "Automation framework uses Playwright Java",
    "Feature files are stored under src/test/resources/features"
]


def search_memory(goal):

    print("\n🧠 Searching Memory...")

    # Simulated relevant-memory retrieval
    memories = MEMORY_STORE[:2]

    print("Relevant Memory:")

    for memory in memories:
        print(" -", memory)

    return memories


def save_memory(memory):

    if memory not in MEMORY_STORE:

        MEMORY_STORE.append(memory)

        print(
            "💾 Memory saved:",
            memory
        )

    else:

        print(
            "ℹ️ Memory already exists:",
            memory
        )


# ============================================================
# 3. PLANNER
# ============================================================

def create_plan():

    return [
        {
            "task": "Read Jira requirement",
            "status": "pending"
        },
        {
            "task": "Inspect repository",
            "status": "pending"
        },
        {
            "task": "Generate missing automation",
            "status": "pending"
        },
        {
            "task": "Run tests",
            "status": "pending"
        },
        {
            "task": "Report result",
            "status": "pending"
        }
    ]


def print_plan(state):

    print("\n📋 PLAN")

    for index, step in enumerate(
        state["plan"],
        start=1
    ):

        print(
            f"{index}. "
            f"{step['task']} "
            f"[{step['status']}]"
        )


# ============================================================
# 4. TOOLS
# ============================================================

def get_jira_issue(issue_key):

    return {
        "status": "success",
        "data": {
            "key": issue_key,
            "summary": "Email validation",
            "workflow_status": "TO BE AUTOMATE"
        }
    }


def inspect_repository():

    return {
        "status": "success",
        "data": {
            "feature": True,
            "step_definition": False,
            "page_object": True
        }
    }


def generate_code(component):

    return {
        "status": "success",
        "component": component,
        "message":
            f"{component} generated successfully"
    }


def run_tests(state):

    state["test_attempts"] += 1

    # First attempt deliberately fails
    if state["test_attempts"] == 1:

        return {
            "status": "failed",
            "error":
                "Compilation error: missing import"
        }

    return {
        "status": "passed",
        "message": "All tests passed"
    }


def fix_code(problem):

    return {
        "status": "success",
        "message":
            f"Code fixed: {problem}"
    }


# ============================================================
# 5. TOOL REGISTRY
# ============================================================

TOOLS = {
    "get_jira_issue": get_jira_issue,
    "inspect_repository": inspect_repository,
    "generate_code": generate_code,
    "run_tests": run_tests,
    "fix_code": fix_code
}


# ============================================================
# 6. GUARDRAILS
# ============================================================

def validate_action(action, state):

    tool = action.get("tool")
    arguments = action.get("arguments", {})

    # Tool must exist
    if tool not in TOOLS:

        return {
            "allowed": False,
            "reason":
                f"Unknown tool: {tool}"
        }

    # Generate only missing components
    if tool == "generate_code":

        component = arguments.get(
            "component"
        )

        if component not in state[
            "missing_components"
        ]:

            return {
                "allowed": False,
                "reason":
                    f"{component} is not missing"
            }

    # Test attempt limit
    if tool == "run_tests":

        if (
            state["test_attempts"]
            >= MAX_TEST_ATTEMPTS
        ):

            return {
                "allowed": False,
                "reason":
                    "Maximum test attempts reached"
            }

    return {
        "allowed": True,
        "reason": "Allowed"
    }


# ============================================================
# 7. TOOL EXECUTOR
# ============================================================

def execute_tool(action, state):

    tool_name = action["tool"]

    arguments = action.get(
        "arguments",
        {}
    )

    tool_function = TOOLS[
        tool_name
    ]

    try:

        # run_tests needs current state
        if tool_name == "run_tests":

            return tool_function(
                state
            )

        return tool_function(
            **arguments
        )

    except Exception as error:

        return {
            "status": "error",
            "error": str(error)
        }


# ============================================================
# 8. UPDATE STATE
# ============================================================

def update_state(
    state,
    action,
    observation
):

    tool = action["tool"]

    state["observations"].append(
        {
            "action": action,
            "observation": observation
        }
    )

    if tool == "get_jira_issue":

        if observation["status"] == "success":

            state["jira_result"] = (
                observation["data"]
            )

    elif tool == "inspect_repository":

        if observation["status"] == "success":

            repository = observation["data"]

            state["repository_result"] = (
                repository
            )

            missing = []

            if not repository["feature"]:
                missing.append("feature")

            if not repository["step_definition"]:
                missing.append(
                    "step_definition"
                )

            if not repository["page_object"]:
                missing.append(
                    "page_object"
                )

            state[
                "missing_components"
            ] = missing

    elif tool == "generate_code":

        if observation["status"] == "success":

            component = observation[
                "component"
            ]

            if component in state[
                "missing_components"
            ]:

                state[
                    "missing_components"
                ].remove(component)

    elif tool == "run_tests":

        if observation["status"] == "failed":

            state["errors"].append(
                observation["error"]
            )


# ============================================================
# 9. REPLANNING
# ============================================================

def replan_after_test_failure(state):

    print(
        "\n🔄 REPLANNING"
    )

    # Original report should not execute yet
    for step in state["plan"]:

        if step["task"] == "Report result":

            step["status"] = "skipped"

    state["plan"].extend(
        [
            {
                "task": "Analyze failure",
                "status": "completed"
            },
            {
                "task": "Fix generated code",
                "status": "pending"
            },
            {
                "task": "Re-run tests",
                "status": "pending"
            },
            {
                "task": "Report final result",
                "status": "pending"
            }
        ]
    )


# ============================================================
# 10. ACTION PROCESSOR
# ============================================================

def process_action(
    action,
    state
):

    # Global Agent limit
    if state["step_count"] >= MAX_STEPS:

        state["status"] = "failed"

        state["stop_reason"] = (
            "Maximum Agent steps reached"
        )

        return None

    state["step_count"] += 1

    print(
        f"\n⚙️ AGENT STEP "
        f"{state['step_count']}"
    )

    print(
        "Decision:",
        action
    )

    # ----------------------------
    # Guardrail
    # ----------------------------

    validation = validate_action(
        action,
        state
    )

    if not validation["allowed"]:

        print(
            "🛑 BLOCKED:",
            validation["reason"]
        )

        state["observations"].append(
            {
                "action": action,
                "observation": {
                    "status": "blocked",
                    "reason":
                        validation["reason"]
                }
            }
        )

        return {
            "status": "blocked"
        }

    # ----------------------------
    # Tool execution
    # ----------------------------

    observation = execute_tool(
        action,
        state
    )

    print(
        "Observation:",
        observation
    )

    # ----------------------------
    # State update
    # ----------------------------

    update_state(
        state,
        action,
        observation
    )

    return observation


# ============================================================
# 11. DECISION LAYER
# ============================================================

def decide_next_action(state):

    """
    Deterministic Decision Layer.

    Later this can be replaced by an LLM.
    """

    # --------------------------------
    # Need Jira?
    # --------------------------------

    if state["jira_result"] is None:

        return {
            "tool": "get_jira_issue",
            "arguments": {
                "issue_key": "QAP-100"
            }
        }

    # --------------------------------
    # Need repository inspection?
    # --------------------------------

    if state["repository_result"] is None:

        return {
            "tool": "inspect_repository",
            "arguments": {}
        }

    # --------------------------------
    # Missing automation?
    # --------------------------------

    if state["missing_components"]:

        return {
            "tool": "generate_code",
            "arguments": {
                "component":
                    state[
                        "missing_components"
                    ][0]
            }
        }

    # --------------------------------
    # Tests haven't run?
    # --------------------------------

    if state["test_attempts"] == 0:

        return {
            "tool": "run_tests",
            "arguments": {}
        }

    return None


# ============================================================
# 12. ORCHESTRATOR
# ============================================================

def run_agent(goal):

    print(
        "\n================================"
    )

    print(
        "🤖 CLEAN SINGLE AGENT"
    )

    print(
        "================================"
    )

    print(
        "\n🎯 GOAL:",
        goal
    )

    # --------------------------------
    # Create State
    # --------------------------------

    state = create_state(goal)

    # --------------------------------
    # Memory → State
    # --------------------------------

    state["relevant_memory"] = (
        search_memory(goal)
    )

    # --------------------------------
    # Planning
    # --------------------------------

    state["plan"] = create_plan()

    print_plan(state)

    # ========================================================
    # ReAct / Agent Loop
    # ========================================================

    while state["status"] == "running":

        action = decide_next_action(
            state
        )

        if action is None:
            break

        observation = process_action(
            action,
            state
        )

        if state["status"] == "failed":
            break

        # --------------------------------
        # Update Plan Progress
        # --------------------------------

        tool = action["tool"]

        if tool == "get_jira_issue":

            state["plan"][0][
                "status"
            ] = "completed"

        elif tool == "inspect_repository":

            state["plan"][1][
                "status"
            ] = "completed"

        elif tool == "generate_code":

            if not state[
                "missing_components"
            ]:

                state["plan"][2][
                    "status"
                ] = "completed"

        elif tool == "run_tests":

            # ================================================
            # TEST FAILED → REPLAN
            # ================================================

            if observation[
                "status"
            ] == "failed":

                state["plan"][3][
                    "status"
                ] = "failed"

                replan_after_test_failure(
                    state
                )

                print_plan(state)

                # --------------------------------------------
                # ReAct: Fix problem
                # --------------------------------------------

                fix_action = {
                    "tool": "fix_code",
                    "arguments": {
                        "problem":
                            observation[
                                "error"
                            ]
                    }
                }

                fix_result = process_action(
                    fix_action,
                    state
                )

                if (
                    fix_result
                    and
                    fix_result["status"]
                    == "success"
                ):

                    state["plan"][6][
                        "status"
                    ] = "completed"

                # --------------------------------------------
                # Re-run tests
                # --------------------------------------------

                retry_action = {
                    "tool": "run_tests",
                    "arguments": {}
                }

                retry_result = process_action(
                    retry_action,
                    state
                )

                if (
                    retry_result
                    and
                    retry_result["status"]
                    == "passed"
                ):

                    state["plan"][7][
                        "status"
                    ] = "completed"

                    state["plan"][8][
                        "status"
                    ] = "completed"

                    state[
                        "status"
                    ] = "success"

                    state[
                        "stop_reason"
                    ] = "Goal completed"

                    state[
                        "final_answer"
                    ] = (
                        "QAP-100 automation "
                        "completed successfully "
                        "and tests passed."
                    )

                else:

                    state["status"] = "failed"

                    state["stop_reason"] = (
                        "Tests failed after recovery"
                    )

            # Tests passed first time
            elif observation[
                "status"
            ] == "passed":

                state["plan"][3][
                    "status"
                ] = "completed"

                state["plan"][4][
                    "status"
                ] = "completed"

                state["status"] = "success"

                state["stop_reason"] = (
                    "Goal completed"
                )

                state["final_answer"] = (
                    "QAP-100 automation "
                    "completed successfully."
                )

    # ========================================================
    # MEMORY WRITE
    # ========================================================

    if state["status"] == "success":

        save_memory(
            "Step definitions for the "
            "input module reuse existing "
            "Page Objects"
        )

    return state


# ============================================================
# 13. RUN
# ============================================================

if __name__ == "__main__":

    result = run_agent(
        "Automate QAP-100"
    )

    print(
        "\n================================"
    )

    print(
        "📋 FINAL PLAN"
    )

    print(
        "================================"
    )

    print_plan(result)

    print(
        "\n================================"
    )

    print(
        "🏁 FINAL STATE"
    )

    print(
        "================================"
    )

    print(
        "Status:",
        result["status"]
    )

    print(
        "Agent Steps:",
        result["step_count"]
    )

    print(
        "Test Attempts:",
        result["test_attempts"]
    )

    print(
        "Stop Reason:",
        result["stop_reason"]
    )

    print(
        "Final Answer:",
        result["final_answer"]
    )