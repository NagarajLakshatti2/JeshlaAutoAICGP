# ==========================================
# Practical Guarded Agent
# ==========================================

MAX_STEPS = 10
MAX_TEST_ATTEMPTS = 3


# ------------------------------------------
# 1. STATE
# ------------------------------------------

def create_state(goal):
    return {
        "goal": goal,

        "step_count": 0,
        "test_attempts": 0,

        "missing_components": [
            "step_definition"
        ],

        "observations": [],
        "errors": [],

        "status": "running",
        "should_stop": False,
        "stop_reason": None,

        "approval_required": False,
        "approval_action": None,
        "approval_status": None,

        "final_answer": None
    }


# ------------------------------------------
# 2. SIMULATED TOOLS
# ------------------------------------------

def search_repository():
    return {
        "feature": True,
        "step_definition": False,
        "page_object": True
    }


def generate_code(component):
    return {
        "status": "success",
        "component": component
    }


def run_tests(state):

    state["test_attempts"] += 1

    # First execution fails.
    if state["test_attempts"] == 1:
        return {
            "status": "failed",
            "error": "Compilation error: missing import"
        }

    # Second execution passes.
    return {
        "status": "passed",
        "message": "All tests passed"
    }


def fix_code():
    return {
        "status": "success",
        "message": "Missing import added"
    }


def create_pr():
    return {
        "status": "success",
        "pr_number": 125
    }


def merge_pr(pr_number):
    return {
        "status": "success",
        "message": f"PR #{pr_number} merged"
    }


# ------------------------------------------
# 3. ACTION GUARDRAIL
# ------------------------------------------

def validate_action(action, state):

    tool = action.get("tool")

    allowed_tools = {
        "search_repository",
        "generate_code",
        "run_tests",
        "fix_code",
        "create_pr",
        "merge_pr"
    }

    # Guardrail 1:
    # Unknown tool
    if tool not in allowed_tools:
        return {
            "allowed": False,
            "reason": f"Tool '{tool}' is not allowed"
        }

    # Guardrail 2:
    # Generation must be justified by State
    if tool == "generate_code":

        component = action.get(
            "arguments", {}
        ).get("component")

        if component not in state["missing_components"]:
            return {
                "allowed": False,
                "reason":
                    f"{component} is not marked as missing"
            }

    # Guardrail 3:
    # Test execution limit
    if tool == "run_tests":

        if state["test_attempts"] >= MAX_TEST_ATTEMPTS:
            return {
                "allowed": False,
                "reason":
                    "Maximum test attempts reached"
            }

    # Guardrail 4:
    # Merge requires human approval
    if tool == "merge_pr":

        if state["approval_status"] != "approved":
            return {
                "allowed": False,
                "approval_required": True,
                "reason":
                    "Human approval required before merge"
            }

    return {
        "allowed": True,
        "reason": "Action permitted"
    }


# ------------------------------------------
# 4. TOOL EXECUTOR
# ------------------------------------------

def execute_tool(action, state):

    tool = action["tool"]
    arguments = action.get("arguments", {})

    if tool == "search_repository":
        return search_repository()

    if tool == "generate_code":
        return generate_code(
            arguments["component"]
        )

    if tool == "run_tests":
        return run_tests(state)

    if tool == "fix_code":
        return fix_code()

    if tool == "create_pr":
        return create_pr()

    if tool == "merge_pr":
        return merge_pr(
            arguments["pr_number"]
        )

    return {
        "status": "error",
        "message": "Unknown tool"
    }


# ------------------------------------------
# 5. EXECUTE ACTION SAFELY
# ------------------------------------------

def execute_action(action, state):

    # Entire Agent step limit
    if state["step_count"] >= MAX_STEPS:

        state["status"] = "failed"
        state["should_stop"] = True
        state["stop_reason"] = (
            "Maximum Agent steps reached"
        )

        return None

    state["step_count"] += 1

    print(
        f"\nSTEP {state['step_count']}"
    )

    print(
        "Proposed Action:",
        action
    )

    validation = validate_action(
        action,
        state
    )

    # --------------------------------------
    # HUMAN APPROVAL REQUIRED
    # --------------------------------------

    if validation.get(
        "approval_required"
    ):

        state["status"] = (
            "waiting_for_approval"
        )

        state["approval_required"] = True

        state["approval_action"] = action

        state["approval_status"] = "pending"

        state["stop_reason"] = (
            validation["reason"]
        )

        print(
            "⏸",
            validation["reason"]
        )

        return None

    # --------------------------------------
    # BLOCKED ACTION
    # --------------------------------------

    if not validation["allowed"]:

        observation = {
            "status": "blocked",
            "reason": validation["reason"]
        }

        state["observations"].append(
            observation
        )

        print(
            "🛑 BLOCKED:",
            validation["reason"]
        )

        return observation

    # --------------------------------------
    # EXECUTE ALLOWED ACTION
    # --------------------------------------

    observation = execute_tool(
        action,
        state
    )

    state["observations"].append(
        observation
    )

    print(
        "Observation:",
        observation
    )

    return observation


# ------------------------------------------
# 6. HUMAN APPROVAL
# ------------------------------------------

def approve_pending_action(state):

    if not state["approval_required"]:
        return

    print(
        "\n👤 Human reviewed the action."
    )

    print(
        "Approved:",
        state["approval_action"]
    )

    state["approval_status"] = "approved"
    state["approval_required"] = False
    state["status"] = "running"
    state["stop_reason"] = None


# ------------------------------------------
# 7. AGENT WORKFLOW
# ------------------------------------------

def run_guarded_agent(goal):

    state = create_state(goal)

    print(
        "\nGOAL:",
        state["goal"]
    )

    # --------------------------------------
    # STEP 1
    # Search repository
    # --------------------------------------

    repository_result = execute_action(
        {
            "tool": "search_repository",
            "arguments": {}
        },
        state
    )

    if state["should_stop"]:
        return state

    # --------------------------------------
    # STEP 2
    # Demonstrate BLOCKED action
    #
    # Page Object already exists.
    # Agent should NOT regenerate it.
    # --------------------------------------

    execute_action(
        {
            "tool": "generate_code",
            "arguments": {
                "component": "page_object"
            }
        },
        state
    )

    # --------------------------------------
    # STEP 3
    # Generate actual missing component
    # --------------------------------------

    generation_result = execute_action(
        {
            "tool": "generate_code",
            "arguments": {
                "component":
                    "step_definition"
            }
        },
        state
    )

    if (
        generation_result
        and
        generation_result.get("status")
        == "success"
    ):
        state["missing_components"].remove(
            "step_definition"
        )

    # --------------------------------------
    # STEP 4
    # First test execution
    # --------------------------------------

    test_result = execute_action(
        {
            "tool": "run_tests",
            "arguments": {}
        },
        state
    )

    # --------------------------------------
    # REPLAN / RECOVERY
    # --------------------------------------

    if (
        test_result
        and
        test_result.get("status")
        == "failed"
    ):

        print(
            "\n🔄 Test failed."
            " Replanning..."
        )

        state["errors"].append(
            test_result["error"]
        )

        # STEP 5
        execute_action(
            {
                "tool": "fix_code",
                "arguments": {}
            },
            state
        )

        # STEP 6
        test_result = execute_action(
            {
                "tool": "run_tests",
                "arguments": {}
            },
            state
        )

    # --------------------------------------
    # TEST SUCCESS?
    # --------------------------------------

    if not test_result:
        return state

    if test_result.get("status") != "passed":

        state["status"] = "failed"
        state["should_stop"] = True
        state["stop_reason"] = (
            "Tests did not pass"
        )

        return state

    # --------------------------------------
    # STEP 7
    # Create PR
    # --------------------------------------

    pr_result = execute_action(
        {
            "tool": "create_pr",
            "arguments": {}
        },
        state
    )

    if not pr_result:
        return state

    pr_number = pr_result["pr_number"]

    # --------------------------------------
    # STEP 8
    # Attempt merge
    #
    # Guardrail should PAUSE.
    # --------------------------------------

    execute_action(
        {
            "tool": "merge_pr",
            "arguments": {
                "pr_number": pr_number
            }
        },
        state
    )

    # --------------------------------------
    # Simulate Human Approval
    # --------------------------------------

    if (
        state["status"]
        == "waiting_for_approval"
    ):

        approve_pending_action(state)

    # --------------------------------------
    # STEP 9
    # Execute EXACT approved action
    # --------------------------------------

    if (
        state["approval_status"]
        == "approved"
    ):

        approved_action = (
            state["approval_action"]
        )

        merge_result = execute_action(
            approved_action,
            state
        )

        if (
            merge_result
            and
            merge_result.get("status")
            == "success"
        ):

            state["status"] = "success"
            state["should_stop"] = True

            state["stop_reason"] = (
                "Goal completed"
            )

            state["final_answer"] = (
                "Automation completed, "
                "tests passed, and "
                f"PR #{pr_number} was merged "
                "after human approval."
            )

    return state


# ------------------------------------------
# 8. START PROGRAM
# ------------------------------------------

if __name__ == "__main__":

    result = run_guarded_agent(
        "Automate QAP-100"
    )

    print(
        "\n========== FINAL STATE =========="
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