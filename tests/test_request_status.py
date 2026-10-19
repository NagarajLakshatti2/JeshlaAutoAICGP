import unittest
from agent.interfaces.request_status import status_label

class RequestStatusTests(unittest.TestCase):
    def test_only_explicit_completion_is_claimed(self):
        self.assertEqual(status_label({}),"Response returned")
        self.assertEqual(status_label({"task_status":"completed"}),"Completed")
        self.assertEqual(status_label({"task_status":"completed","execution_outcome":"blocked"}),"Incomplete")
        self.assertEqual(status_label({"task_status":"awaiting_input"}),"Waiting for your input or approval")
        self.assertEqual(status_label({"task_status":"incomplete"}),"Incomplete")
        self.assertEqual(status_label({"task_status":"failed"}),"Failed")
