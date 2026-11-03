import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from handlers.common import validate, authorize
from handlers.provider import simulate, TemporaryUpstreamError, UpstreamTimeoutError, PermanentUpstreamError
from handlers import submit, status, result

OWNER = "arn:aws:iam::123456789012:user/example"
def evt(body=None, request_id="abc"):
    event = {"requestContext": {"identity": {"userArn": OWNER}}, "pathParameters": {"requestId": request_id}}
    if body is not None:
        event["body"] = json.dumps(body)
    return event
PAYLOAD = {"service": "automotive-data-center", "operation": "get-vehicle-status", "parameters": {"vehicleId": "vehicle-12345"}}

class TestEDR(unittest.TestCase):
    def setUp(self):
        self.policy = patch.dict(os.environ, {
            "EDR_ALLOWED_OPERATIONS": json.dumps({
                OWNER: ["get-vehicle-status", "get-recalls"]
            })
        })
        self.policy.start()
        self.addCleanup(self.policy.stop)

    def test_validate(self):
        self.assertEqual(validate(PAYLOAD), PAYLOAD)
        with self.assertRaises(ValueError): validate({"service": "other"})
    def test_mock_success(self):
        self.assertEqual(simulate("get-vehicle-status", "vehicle-1")["statusCode"], 200)
    def test_mock_429_retry_after(self):
        self.assertEqual(simulate("get-vehicle-status", "vehicle-1", "429_once", 0)["retryAfterSeconds"], 2)
        self.assertEqual(simulate("get-vehicle-status", "vehicle-1", "429_once", 1)["statusCode"], 200)
        self.assertEqual(simulate("get-vehicle-status", "vehicle-1", "429_always", 3)["statusCode"], 429)
    def test_mock_5xx_timeout_permanent(self):
        for mode, klass in [("500",TemporaryUpstreamError),("timeout",UpstreamTimeoutError),("unauthorized",PermanentUpstreamError),("invalid",PermanentUpstreamError)]:
            with self.subTest(mode=mode), self.assertRaises(klass): simulate("get-vehicle-status", "vehicle-1", mode)
    def test_submit_rejects_invalid(self):
        self.assertEqual(submit.handler(evt({"bad":True}), None)["statusCode"], 400)
    def test_submit_rejects_unauthenticated(self):
        self.assertEqual(submit.handler({"body": json.dumps(PAYLOAD)}, None)["statusCode"], 403)
    @patch("handlers.submit.get_table")
    def test_submit_success(self, table):
        with patch.dict(os.environ,{"STATE_MACHINE_ARN":"arn:example"}), patch("boto3.client") as client:
            response = submit.handler(evt(PAYLOAD), None)
        self.assertEqual(response["statusCode"],202)
        self.assertEqual(json.loads(response["body"])["status"], "PENDING")
        table.return_value.put_item.assert_called_once()
        client.return_value.start_execution.assert_called_once()
    @patch("handlers.status.get_table")
    def test_status(self, table):
        table.return_value.get_item.return_value={"Item":{"owner":OWNER,"status":"RUNNING"}}
        self.assertEqual(json.loads(status.handler(evt(),None)["body"])["status"],"RUNNING")
    @patch("handlers.result.get_table")
    def test_result_only_after_success(self, table):
        table.return_value.get_item.return_value={"Item":{"owner":OWNER,"status":"PENDING"}}
        self.assertEqual(result.handler(evt(),None)["statusCode"],409)
        table.return_value.get_item.return_value={"Item":{"owner":OWNER,"status":"SUCCEEDED","result":{"ok":True}}}
        self.assertEqual(result.handler(evt(),None)["statusCode"],200)
    @patch("handlers.status.get_table")
    def test_other_user_cannot_read(self, table):
        table.return_value.get_item.return_value={"Item":{"owner":"someone-else","status":"SUCCEEDED"}}
        self.assertEqual(status.handler(evt(),None)["statusCode"],404)
    def test_workflow_structure(self):
        from pathlib import Path
        workflow=json.loads((Path(__file__).resolve().parents[1]/"stepfunctions/workflow.asl.json").read_text())
        s=workflow["States"]
        self.assertEqual(s["WaitRetryAfter"]["SecondsPath"],"$.upstream.Payload.retryAfterSeconds")
        self.assertEqual(s["CheckRetryBudget"]["Choices"][0]["NumericGreaterThanEquals"],3)
        self.assertEqual(s["InvokeProvider"]["Retry"][0]["MaxAttempts"],3)


    def test_authorize_allowed(self):
        self.assertTrue(authorize(OWNER, PAYLOAD))

    def test_authorize_forbidden_operation(self):
        payload = {**PAYLOAD, "operation": "get-service-history"}
        with self.assertRaises(PermissionError):
            authorize(OWNER, payload)

    def test_authorize_unknown_user(self):
        with self.assertRaises(PermissionError):
            authorize("arn:aws:iam::123456789012:user/unknown", PAYLOAD)

    def test_authorize_deny_by_default(self):
        with patch.dict(os.environ, {"EDR_ALLOWED_OPERATIONS": "{}"}):
            with self.assertRaises(PermissionError):
                authorize(OWNER, PAYLOAD)

    def test_authorize_invalid_policy(self):
        with patch.dict(os.environ, {"EDR_ALLOWED_OPERATIONS": "invalid-json"}):
            with self.assertRaises(PermissionError):
                authorize(OWNER, PAYLOAD)

if __name__=="__main__": unittest.main()
