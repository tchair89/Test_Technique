# Evidence of verification

Fill with ACTUAL outputs after running commands. Do not claim AWS execution without an actual deployment.

| Check | Command | Actual result |
|---|---|---|
| Python unit tests | `python -m unittest discover -s tests -v` | PASS — 11 tests (voir `python-tests-output.txt`) |
| Terraform formatting | `terraform fmt -check -recursive` (from terraform/) | TODO |
| Terraform validate | `terraform validate` | TODO |
| Terraform offline plan | `terraform plan -refresh=false -var-file=environments/dev.tfvars -out=edr.tfplan` | TODO |
| AWS Step Functions execution | Not executed (no deployment) | NOT RUN |

Limits: local mock tests and structural ASL assertions are not the same as successful deployment/integration on AWS.
