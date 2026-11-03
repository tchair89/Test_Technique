# EDR — AWS External Data Retrieval (technical assignment)

Asynchronous vehicle-data retrieval API implemented with Python Lambda handlers, AWS Step Functions Standard, API Gateway REST, DynamoDB, IAM and Terraform. **This repository is designed for a no-deployment assignment; do not run `terraform apply` unless explicitly authorized.**

## Prerequisites

- Python 3.11+, Git, Terraform >=1.5, network access for Terraform provider initialization.
- AWS credentials are not required for the **offline plan** configuration. `terraform init` still downloads provider plugins. No deployment or AWS runtime execution is claimed.

## Local tests (Git Bash on Windows)

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Terraform offline verification

```bash
cd terraform
terraform init -backend=false
terraform fmt -recursive
terraform validate
terraform plan -refresh=false -var-file=environments/dev.tfvars -out=edr.tfplan
terraform show -no-color edr.tfplan > ../docs/terraform-plan.txt
```

Do not commit state, binary plan files, credentials or secrets. `offline_plan=true` uses deliberately invalid synthetic credentials to allow reviewing a speculative plan without contacting AWS; this is **not** proof of cloud deployability. Some provider versions may still require extra online checks. Turn it off and use a properly authorized test account for a real deployment.

## API contract

Authentication: API Gateway IAM / AWS Signature V4. Each caller needs a separately granted `execute-api:Invoke` policy. Local tests inject a fictional authenticated requestContext.

```http
POST /requests
Content-Type: application/json

{"service":"automotive-data-center","operation":"get-vehicle-status","parameters":{"vehicleId":"vehicle-12345"}}
```

Response `202`: `{"requestId":"<uuid>","status":"PENDING"}`.

`GET /requests/{requestId}` -> `200` `PENDING | RUNNING | SUCCEEDED | FAILED`; a failure includes an error.

`GET /requests/{requestId}/result` -> `200` normalized result if `SUCCEEDED`, otherwise `409`.

Unknown requests and other owners return `404`. Malformed/unsupported submissions `400`; missing/denied caller `403`. API Gateway throttling returns `429` when configured limits are exceeded.

## Mock scenarios

In `parameters`, optionally set `simulate` to `success`, `429_once`, `429_always`, `500`, `timeout`, `unauthorized`, or `invalid`. This is for test only, not for a real public provider API. Fictional data only.

## Workflow

1. Initial API validates caller and request, creates PENDING item, starts state machine, returns request ID.
2. State machine marks RUNNING, runs validate + authorize, then mock provider.
3. For 429: dynamic `Wait` honoring numeric `retryAfterSeconds` (mock uses 2) then max 3 retries. In production, normalize and bound the upstream HTTP `Retry-After` header (delta-seconds or HTTP-date) before feeding `SecondsPath`.
4. For 5xx/timeout: exponential retry via Step Functions `Retry`, bounded at 3 attempts, then failure handler.
5. Success handler normalizes payload and stores data; failure handler stores FAILED. Status/result Lambda enforce owner-based visibility.

## Environment strategy

`terraform/environments/dev.tfvars` configures development. Add e.g. `eacc.tfvars` with a distinct environment name and rate limits. Separate state/backends and credentials for real per-environment deployments; no remote state backend is configured for this assignment.

## Security and limitations

No credential values are included in source code, Terraform vars or logs. A Secrets Manager secret is declared but empty, because the mock needs no credentials. IAM role policies are defined per handler, with per-resource restrictions. CloudWatch log access and Step Functions logging policy follow AWS managed-service constraints. See `docs/architecture.md` for trade-offs.

Known non-production shortcuts: static allowed-operation policy instead of external entitlements, IAM ARN ownership model, no authorizer user-registration workflow, no distributed rate limit counter in mock Lambda, no deployed AWS integration tests, no strict runtime JSON schema.

## Submission

Send the ZIP or private repository URL together with `docs/architecture.md` and filled `docs/test-results.md`. State clearly which checks were actually executed; never present an offline speculative plan as a validated production deployment.
