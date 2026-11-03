import json
import os
import re
import uuid
from datetime import datetime, timezone

ALLOWED = {"get-vehicle-status", "get-service-history", "get-recalls"}
SERVICE = "automotive-data-center"

def validate(payload):
    if not isinstance(payload, dict) or payload.get("service") != SERVICE or payload.get("operation") not in ALLOWED:
        raise ValueError("Unsupported service or operation")
    params = payload.get("parameters")
    if not isinstance(params, dict) or not isinstance(params.get("vehicleId"), str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", params["vehicleId"]):
        raise ValueError("parameters.vehicleId is required and must contain 1-64 letters, digits or hyphens")
    if params.get("simulate", "success") not in ("success", "429_once", "429_always", "500", "timeout", "unauthorized", "invalid"):
        raise ValueError("Invalid simulation mode")
    return payload

def owner_from_event(event):
    owner = event.get("requestContext", {}).get("identity", {}).get("userArn")
    if not owner:
        raise PermissionError("IAM authentication required")
    return owner

def authorize(owner, payload):
    if not owner:
        raise PermissionError("IAM authentication required")

    if (
        payload.get("service") != SERVICE
        or payload.get("operation") not in ALLOWED
    ):
        raise PermissionError("Service or operation not authorized")

    try:
        policies = json.loads(
            os.environ.get("EDR_ALLOWED_OPERATIONS", "{}")
        )
    except (ValueError, TypeError):
        raise PermissionError("Invalid authorization policy")

    if not isinstance(policies, dict):
        raise PermissionError("Invalid authorization policy")

    allowed_operations = policies.get(owner, [])

    if not isinstance(allowed_operations, list):
        raise PermissionError("Invalid authorization policy")

    if payload["operation"] not in allowed_operations:
        raise PermissionError(
            "User not authorized for this operation"
        )

    return True

def response(code, obj):
    return {"statusCode": code, "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"}, "body": json.dumps(obj)}

def now():
    return datetime.now(timezone.utc).isoformat()

def get_table():
    import boto3
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def parse_body(event):
    try:
        return json.loads(event.get("body") or "{}")
    except (TypeError, json.JSONDecodeError):
        raise ValueError("Malformed JSON")
