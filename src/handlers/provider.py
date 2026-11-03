class TemporaryUpstreamError(Exception):
    pass

class UpstreamTimeoutError(Exception):
    pass

class PermanentUpstreamError(Exception):
    pass

def simulate(operation, vehicle_id, mode="success", attempt=0):
    if mode == "429_always" or (mode == "429_once" and attempt == 0):
        return {"statusCode": 429, "retryAfterSeconds": 2}
    if mode == "500":
        raise TemporaryUpstreamError("Simulated upstream HTTP 503")
    if mode == "timeout":
        raise UpstreamTimeoutError("Simulated upstream timeout")
    if mode == "unauthorized":
        raise PermanentUpstreamError("Simulated upstream HTTP 403")
    if mode == "invalid":
        raise PermanentUpstreamError("Simulated upstream HTTP 400")
    data = {
        "get-vehicle-status": {"vehicleId": vehicle_id, "status": "ACTIVE", "mileageKm": 25400},
        "get-service-history": {"vehicleId": vehicle_id, "services": [{"date": "2025-06-15", "type": "inspection"}]},
        "get-recalls": {"vehicleId": vehicle_id, "recalls": []},
    }
    return {"statusCode": 200, "data": data[operation]}

def handler(event, context):
    return simulate(event["operation"], event["parameters"]["vehicleId"],
                    event["parameters"].get("simulate", "success"), event.get("attempt", 0))
