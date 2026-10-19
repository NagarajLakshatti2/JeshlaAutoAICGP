import io
from contextlib import redirect_stdout
import unittest
from agent.timing import timer,timed


class TimingTests(unittest.TestCase):
    def capture(self,function):
        output=io.StringIO()
        with redirect_stdout(output):result=function()
        return result,output.getvalue()

    def test_incomplete_return_is_not_success(self):
        @timed("project")
        def task():return {"answer":"Stopped","task_status":"incomplete"}
        result,log=self.capture(task)
        self.assertEqual(result["answer"],"Stopped")
        self.assertIn("| INCOMPLETE |",log)
        self.assertNotIn("| SUCCESS |",log)

    def test_existing_success_behavior_preserved(self):
        @timed("router")
        def task():return {"route":"project"}
        result,log=self.capture(task)
        self.assertEqual(result["route"],"project")
        self.assertIn("| SUCCESS |",log)

    def test_exception_still_propagates(self):
        @timed("model")
        def task():raise RuntimeError("offline error")
        output=io.StringIO()
        with redirect_stdout(output),self.assertRaises(RuntimeError):task()
        self.assertIn("FAILED / INTERRUPTED",output.getvalue())

    def test_outer_workflow_observes_result(self):
        output=io.StringIO()
        with redirect_stdout(output):
            with timer("workflow") as outcome:
                outcome.observe({"task_status":"incomplete"})
        self.assertIn("| INCOMPLETE |",output.getvalue())
