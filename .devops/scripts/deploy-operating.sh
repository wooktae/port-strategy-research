#!/usr/bin/env bash

set -euo pipefail

SOURCE_SHA="${1:?SOURCE_SHA is required}"
AWS_REGION="${2:?AWS_REGION is required}"
ECR_REPOSITORY_NAME="${3:?ECR_REPOSITORY_NAME is required}"
OPERATING_JOB_DEFINITION_NAME="${4:?OPERATING_JOB_DEFINITION_NAME is required}"

if [[ ! "${SOURCE_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_SHA_INVALID=${SOURCE_SHA}"
  exit 10
fi

SHORT_SHA="${SOURCE_SHA:0:12}"

echo "=== RESOLVE VERIFIED ECR ARTIFACT ==="

AWS_ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --query Account \
    --output text
)"

if [[ ! "${AWS_ACCOUNT_ID}" =~ ^[0-9]{12}$ ]]; then
  echo "AWS_ACCOUNT_ID_INVALID=${AWS_ACCOUNT_ID}"
  exit 11
fi

IMAGE_DIGEST="$(
  aws ecr describe-images \
    --region "${AWS_REGION}" \
    --repository-name "${ECR_REPOSITORY_NAME}" \
    --image-ids imageTag="${SHORT_SHA}" \
    --query 'imageDetails[0].imageDigest' \
    --output text
)"

if [[ ! "${IMAGE_DIGEST}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "IMAGE_DIGEST_INVALID=${IMAGE_DIGEST}"
  exit 12
fi

IMAGE_URI="$(
  printf '%s.dkr.ecr.%s.amazonaws.com/%s@%s' \
    "${AWS_ACCOUNT_ID}" \
    "${AWS_REGION}" \
    "${ECR_REPOSITORY_NAME}" \
    "${IMAGE_DIGEST}"
)"

echo "SOURCE_SHA=${SOURCE_SHA}"
echo "IMAGE_DIGEST=${IMAGE_DIGEST}"
echo "ECR_ARTIFACT_IDENTITY=SUCCESS"

echo
echo "=== RESOLVE OPERATING BASELINE ==="

aws batch describe-job-definitions \
  --region "${AWS_REGION}" \
  --job-definition-name "${OPERATING_JOB_DEFINITION_NAME}" \
  --status ACTIVE \
  --output json \
  > /tmp/research-operating-definitions.json

OPERATING_COUNT="$(
  jq '.jobDefinitions | length' \
    /tmp/research-operating-definitions.json
)"

if [[ "${OPERATING_COUNT}" -lt 1 ]]; then
  echo "ACTIVE_OPERATING_JOB_DEFINITION_NOT_FOUND"
  exit 20
fi

jq '
  .jobDefinitions
  | sort_by(.revision)
  | reverse
  | .[0]
' /tmp/research-operating-definitions.json \
  > /tmp/research-operating-baseline.json

BASELINE_REVISION="$(
  jq -r '.revision' \
    /tmp/research-operating-baseline.json
)"

BASELINE_CONFIG_VERSION="$(
  jq -r '
    .containerProperties.command as $cmd
    | ($cmd | index("--strategy-config-version")) as $i
    | if $i == null then empty else $cmd[$i + 1] end
  ' /tmp/research-operating-baseline.json
)"

if [[ ! "${BASELINE_REVISION}" =~ ^[0-9]+$ ]]; then
  echo "OPERATING_BASELINE_REVISION_INVALID=${BASELINE_REVISION}"
  exit 21
fi

if [[ ! "${BASELINE_CONFIG_VERSION}" =~ ^RSCFG-[0-9]{4}$ ]]; then
  echo "OPERATING_BASELINE_CONFIG_VERSION_INVALID=${BASELINE_CONFIG_VERSION}"
  exit 22
fi

echo "OPERATING_BASELINE_REVISION=${BASELINE_REVISION}"
echo "OPERATING_STRATEGY_CONFIG_VERSION=${BASELINE_CONFIG_VERSION}"
echo "OPERATING_BASELINE_RESOLUTION=SUCCESS"

echo
echo "=== PREPARE OPERATING JOB DEFINITION ==="

jq \
  --arg image_uri "${IMAGE_URI}" \
  --arg source_sha "${SOURCE_SHA}" \
  --arg image_digest "${IMAGE_DIGEST}" \
  '
  {
    jobDefinitionName: .jobDefinitionName,
    type: .type,

    containerProperties:
      (
        .containerProperties

        | .image = $image_uri

        | .environment =
          (
            (
              (.environment // [])
              | map(
                  select(
                    .name != "RESEARCH_SOURCE_SHA"
                    and
                    .name != "RESEARCH_IMAGE_DIGEST"
                  )
                )
            )
            +
            [
              {
                name: "RESEARCH_SOURCE_SHA",
                value: $source_sha
              },
              {
                name: "RESEARCH_IMAGE_DIGEST",
                value: $image_digest
              }
            ]
          )
      ),

    platformCapabilities: .platformCapabilities
  }

  + (
      if (.parameters? != null and .parameters != {})
      then {parameters: .parameters}
      else {}
      end
    )

  + (
      if (.retryStrategy? != null)
      then {retryStrategy: .retryStrategy}
      else {}
      end
    )

  + (
      if (.timeout? != null and .timeout != {})
      then {timeout: .timeout}
      else {}
      end
    )

  + (
      if (.propagateTags? != null)
      then {propagateTags: .propagateTags}
      else {}
      end
    )

  + (
      if (.tags? != null and .tags != {})
      then {tags: .tags}
      else {}
      end
    )
  ' \
  /tmp/research-operating-baseline.json \
  > /tmp/research-operating-register.json

PREPARED_CONFIG_VERSION="$(
  jq -r '
    .containerProperties.command as $cmd
    | ($cmd | index("--strategy-config-version")) as $i
    | if $i == null then empty else $cmd[$i + 1] end
  ' /tmp/research-operating-register.json
)"

PREPARED_IMAGE="$(
  jq -r '.containerProperties.image' \
    /tmp/research-operating-register.json
)"

PREPARED_SOURCE_SHA="$(
  jq -r '
    .containerProperties.environment[]
    | select(.name == "RESEARCH_SOURCE_SHA")
    | .value
  ' /tmp/research-operating-register.json
)"

PREPARED_IMAGE_DIGEST="$(
  jq -r '
    .containerProperties.environment[]
    | select(.name == "RESEARCH_IMAGE_DIGEST")
    | .value
  ' /tmp/research-operating-register.json
)"

if [[ "${PREPARED_CONFIG_VERSION}" != "${BASELINE_CONFIG_VERSION}" ]]; then
  echo "OPERATING_CONFIG_VERSION_CHANGED"
  exit 30
fi

if [[ "${PREPARED_IMAGE}" != "${IMAGE_URI}" ]]; then
  echo "OPERATING_PREPARED_IMAGE_MISMATCH"
  exit 31
fi

if [[ "${PREPARED_SOURCE_SHA}" != "${SOURCE_SHA}" ]]; then
  echo "OPERATING_PREPARED_SOURCE_SHA_MISMATCH"
  exit 32
fi

if [[ "${PREPARED_IMAGE_DIGEST}" != "${IMAGE_DIGEST}" ]]; then
  echo "OPERATING_PREPARED_IMAGE_DIGEST_MISMATCH"
  exit 33
fi

echo "OPERATING_CONFIG_VERSION_PRESERVED=${BASELINE_CONFIG_VERSION}"
echo "OPERATING_RUNTIME_BASELINE_COPIED=SUCCESS"
echo "OPERATING_ARTIFACT_IDENTITY_INJECTED=SUCCESS"

echo
echo "=== PREFLIGHT OPERATING RUNTIME REFERENCES ==="

EXPECTED_BASELINE_ARN="$(
  jq -r '.jobDefinitionArn' \
    /tmp/research-operating-baseline.json
)"

PRODUCTION_STATE_MACHINE_NAME="portfolio-paper-daily-step1-17-approval"
STEP4_ONLY_STATE_MACHINE_NAME="portfolio-paper-daily-step4-only"

PRODUCTION_STATE_MACHINE_ARN="$(
  aws stepfunctions list-state-machines \
    --region "${AWS_REGION}" \
    --query "stateMachines[?name=='${PRODUCTION_STATE_MACHINE_NAME}'].stateMachineArn | [0]" \
    --output text
)"

STEP4_ONLY_STATE_MACHINE_ARN="$(
  aws stepfunctions list-state-machines \
    --region "${AWS_REGION}" \
    --query "stateMachines[?name=='${STEP4_ONLY_STATE_MACHINE_NAME}'].stateMachineArn | [0]" \
    --output text
)"

if [[ -z "${PRODUCTION_STATE_MACHINE_ARN}" ||
      "${PRODUCTION_STATE_MACHINE_ARN}" == "None" ]]; then
  echo "PRODUCTION_STATE_MACHINE_NOT_FOUND=${PRODUCTION_STATE_MACHINE_NAME}"
  exit 34
fi

if [[ -z "${STEP4_ONLY_STATE_MACHINE_ARN}" ||
      "${STEP4_ONLY_STATE_MACHINE_ARN}" == "None" ]]; then
  echo "STEP4_ONLY_STATE_MACHINE_NOT_FOUND=${STEP4_ONLY_STATE_MACHINE_NAME}"
  exit 35
fi

PRODUCTION_PREFLIGHT_DEFINITION="$(
  aws stepfunctions describe-state-machine \
    --region "${AWS_REGION}" \
    --state-machine-arn "${PRODUCTION_STATE_MACHINE_ARN}" \
    --query 'definition' \
    --output text
)"

STEP4_ONLY_PREFLIGHT_DEFINITION="$(
  aws stepfunctions describe-state-machine \
    --region "${AWS_REGION}" \
    --state-machine-arn "${STEP4_ONLY_STATE_MACHINE_ARN}" \
    --query 'definition' \
    --output text
)"

PRODUCTION_PREFLIGHT_JOBDEF="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    <<< "${PRODUCTION_PREFLIGHT_DEFINITION}"
)"

STEP4_ONLY_PREFLIGHT_JOBDEF="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    <<< "${STEP4_ONLY_PREFLIGHT_DEFINITION}"
)"

if [[ "${PRODUCTION_PREFLIGHT_JOBDEF}" != "${EXPECTED_BASELINE_ARN}" ]]; then
  echo "PRODUCTION_PREFLIGHT_BASELINE_MISMATCH"
  echo "EXPECTED=${EXPECTED_BASELINE_ARN}"
  echo "ACTUAL=${PRODUCTION_PREFLIGHT_JOBDEF}"
  exit 36
fi

if [[ "${STEP4_ONLY_PREFLIGHT_JOBDEF}" != "${EXPECTED_BASELINE_ARN}" ]]; then
  echo "STEP4_ONLY_PREFLIGHT_BASELINE_MISMATCH"
  echo "EXPECTED=${EXPECTED_BASELINE_ARN}"
  echo "ACTUAL=${STEP4_ONLY_PREFLIGHT_JOBDEF}"
  exit 37
fi

echo "PRODUCTION_PREFLIGHT_JOB_DEFINITION=${PRODUCTION_PREFLIGHT_JOBDEF}"
echo "STEP4_ONLY_PREFLIGHT_JOB_DEFINITION=${STEP4_ONLY_PREFLIGHT_JOBDEF}"
echo "OPERATING_DUAL_STATE_MACHINE_PREFLIGHT=SUCCESS"

echo
echo "=== REGISTER OPERATING JOB DEFINITION ==="

REGISTER_RESULT="$(
  aws batch register-job-definition \
    --region "${AWS_REGION}" \
    --cli-input-json file:///tmp/research-operating-register.json
)"

OPERATING_JOB_DEFINITION_ARN="$(
  jq -r '.jobDefinitionArn' <<< "${REGISTER_RESULT}"
)"

OPERATING_REVISION="$(
  jq -r '.revision' <<< "${REGISTER_RESULT}"
)"

if [[ -z "${OPERATING_JOB_DEFINITION_ARN}" ||
      "${OPERATING_JOB_DEFINITION_ARN}" == "null" ]]; then
  echo "OPERATING_JOB_DEFINITION_ARN_EMPTY"
  exit 40
fi

if [[ ! "${OPERATING_REVISION}" =~ ^[0-9]+$ ]]; then
  echo "OPERATING_REVISION_INVALID=${OPERATING_REVISION}"
  exit 41
fi

echo "OPERATING_REVISION=${OPERATING_REVISION}"
echo "OPERATING_JOB_DEFINITION_ARN=${OPERATING_JOB_DEFINITION_ARN}"
echo "OPERATING_JOB_DEFINITION_REGISTRATION=SUCCESS"

echo
echo "=== RESOLVE PRODUCTION STATE MACHINE ==="

PRODUCTION_STATE_MACHINE_NAME="portfolio-paper-daily-step1-17-approval"

PRODUCTION_STATE_MACHINE_ARN="$(
  aws stepfunctions list-state-machines \
    --region "${AWS_REGION}" \
    --query "stateMachines[?name=='${PRODUCTION_STATE_MACHINE_NAME}'].stateMachineArn | [0]" \
    --output text
)"

if [[ -z "${PRODUCTION_STATE_MACHINE_ARN}" ||
      "${PRODUCTION_STATE_MACHINE_ARN}" == "None" ]]; then
  echo "PRODUCTION_STATE_MACHINE_NOT_FOUND=${PRODUCTION_STATE_MACHINE_NAME}"
  exit 50
fi

echo "PRODUCTION_STATE_MACHINE=${PRODUCTION_STATE_MACHINE_NAME}"
echo "PRODUCTION_STATE_MACHINE_ARN=${PRODUCTION_STATE_MACHINE_ARN}"

echo
echo "=== VERIFY PRODUCTION BASELINE ==="

aws stepfunctions describe-state-machine \
  --region "${AWS_REGION}" \
  --state-machine-arn "${PRODUCTION_STATE_MACHINE_ARN}" \
  --query 'definition' \
  --output text \
  > /tmp/research-production-definition.json

CURRENT_STEP4_JOB_DEFINITION="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    /tmp/research-production-definition.json
)"

EXPECTED_BASELINE_ARN="$(
  jq -r '.jobDefinitionArn' \
    /tmp/research-operating-baseline.json
)"

if [[ -z "${CURRENT_STEP4_JOB_DEFINITION}" ]]; then
  echo "PRODUCTION_STEP4_JOB_DEFINITION_EMPTY"
  exit 51
fi

if [[ "${CURRENT_STEP4_JOB_DEFINITION}" != "${EXPECTED_BASELINE_ARN}" ]]; then
  echo "PRODUCTION_STALE_BASELINE_GUARD=FAILED"
  echo "EXPECTED_STEP4_JOB_DEFINITION=${EXPECTED_BASELINE_ARN}"
  echo "ACTUAL_STEP4_JOB_DEFINITION=${CURRENT_STEP4_JOB_DEFINITION}"
  exit 52
fi

echo "CURRENT_STEP4_JOB_DEFINITION=${CURRENT_STEP4_JOB_DEFINITION}"
echo "PRODUCTION_STALE_BASELINE_GUARD=SUCCESS"

echo
echo "=== PREPARE PRODUCTION STEP4 UPDATE ==="

jq \
  --arg new_job_definition "${OPERATING_JOB_DEFINITION_ARN}" \
  '
    .States.Step4_SubmitBacktestResearch.Parameters.JobDefinition
      = $new_job_definition
  ' \
  /tmp/research-production-definition.json \
  > /tmp/research-production-definition-updated.json

PREPARED_STEP4_JOB_DEFINITION="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    /tmp/research-production-definition-updated.json
)"

if [[ "${PREPARED_STEP4_JOB_DEFINITION}" != "${OPERATING_JOB_DEFINITION_ARN}" ]]; then
  echo "PRODUCTION_STEP4_PREPARE_MISMATCH"
  exit 53
fi

echo "PREVIOUS_STEP4_JOB_DEFINITION=${CURRENT_STEP4_JOB_DEFINITION}"
echo "TARGET_STEP4_JOB_DEFINITION=${OPERATING_JOB_DEFINITION_ARN}"
echo "PRODUCTION_STEP4_PREPARE=SUCCESS"

echo
echo "=== UPDATE PRODUCTION STEP4 ==="

aws stepfunctions update-state-machine \
  --region "${AWS_REGION}" \
  --state-machine-arn "${PRODUCTION_STATE_MACHINE_ARN}" \
  --definition file:///tmp/research-production-definition-updated.json \
  > /tmp/research-production-update-result.json

echo "PRODUCTION_STATE_MACHINE_UPDATE_REQUEST=SUCCESS"

echo
echo "=== VERIFY PRODUCTION STEP4 AFTER UPDATE ==="

aws stepfunctions describe-state-machine \
  --region "${AWS_REGION}" \
  --state-machine-arn "${PRODUCTION_STATE_MACHINE_ARN}" \
  --query 'definition' \
  --output text \
  > /tmp/research-production-definition-after.json

AFTER_STEP4_JOB_DEFINITION="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    /tmp/research-production-definition-after.json
)"

if [[ "${AFTER_STEP4_JOB_DEFINITION}" != "${OPERATING_JOB_DEFINITION_ARN}" ]]; then
  echo "PRODUCTION_STEP4_AFTER_CHECK_FAILED"
  echo "EXPECTED=${OPERATING_JOB_DEFINITION_ARN}"
  echo "ACTUAL=${AFTER_STEP4_JOB_DEFINITION}"
  exit 54
fi

echo "PRODUCTION_STEP4_JOB_DEFINITION=${AFTER_STEP4_JOB_DEFINITION}"
echo "PRODUCTION_STEP4_AFTER_CHECK=SUCCESS"

echo
echo "=== RESOLVE STEP4-ONLY STATE MACHINE ==="

STEP4_ONLY_STATE_MACHINE_NAME="portfolio-paper-daily-step4-only"

STEP4_ONLY_STATE_MACHINE_ARN="$(
  aws stepfunctions list-state-machines \
    --region "${AWS_REGION}" \
    --query "stateMachines[?name=='${STEP4_ONLY_STATE_MACHINE_NAME}'].stateMachineArn | [0]" \
    --output text
)"

if [[ -z "${STEP4_ONLY_STATE_MACHINE_ARN}" ||
      "${STEP4_ONLY_STATE_MACHINE_ARN}" == "None" ]]; then
  echo "STEP4_ONLY_STATE_MACHINE_NOT_FOUND=${STEP4_ONLY_STATE_MACHINE_NAME}"
  exit 60
fi

echo "STEP4_ONLY_STATE_MACHINE=${STEP4_ONLY_STATE_MACHINE_NAME}"
echo "STEP4_ONLY_STATE_MACHINE_ARN=${STEP4_ONLY_STATE_MACHINE_ARN}"

echo
echo "=== VERIFY STEP4-ONLY BASELINE ==="

aws stepfunctions describe-state-machine \
  --region "${AWS_REGION}" \
  --state-machine-arn "${STEP4_ONLY_STATE_MACHINE_ARN}" \
  --query 'definition' \
  --output text \
  > /tmp/research-step4-only-definition.json

CURRENT_STEP4_ONLY_JOB_DEFINITION="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    /tmp/research-step4-only-definition.json
)"

if [[ -z "${CURRENT_STEP4_ONLY_JOB_DEFINITION}" ]]; then
  echo "STEP4_ONLY_JOB_DEFINITION_EMPTY"
  exit 61
fi

if [[ "${CURRENT_STEP4_ONLY_JOB_DEFINITION}" != "${EXPECTED_BASELINE_ARN}" ]]; then
  echo "STEP4_ONLY_STALE_BASELINE_GUARD=FAILED"
  echo "EXPECTED_STEP4_ONLY_JOB_DEFINITION=${EXPECTED_BASELINE_ARN}"
  echo "ACTUAL_STEP4_ONLY_JOB_DEFINITION=${CURRENT_STEP4_ONLY_JOB_DEFINITION}"
  exit 62
fi

echo "CURRENT_STEP4_ONLY_JOB_DEFINITION=${CURRENT_STEP4_ONLY_JOB_DEFINITION}"
echo "STEP4_ONLY_STALE_BASELINE_GUARD=SUCCESS"

echo
echo "=== PREPARE STEP4-ONLY UPDATE ==="

jq \
  --arg new_job_definition "${OPERATING_JOB_DEFINITION_ARN}" \
  '
    .States.Step4_SubmitBacktestResearch.Parameters.JobDefinition
      = $new_job_definition
  ' \
  /tmp/research-step4-only-definition.json \
  > /tmp/research-step4-only-definition-updated.json

PREPARED_STEP4_ONLY_JOB_DEFINITION="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    /tmp/research-step4-only-definition-updated.json
)"

if [[ "${PREPARED_STEP4_ONLY_JOB_DEFINITION}" != "${OPERATING_JOB_DEFINITION_ARN}" ]]; then
  echo "STEP4_ONLY_PREPARE_MISMATCH"
  exit 63
fi

echo "STEP4_ONLY_PREVIOUS_JOB_DEFINITION=${CURRENT_STEP4_ONLY_JOB_DEFINITION}"
echo "STEP4_ONLY_TARGET_JOB_DEFINITION=${OPERATING_JOB_DEFINITION_ARN}"
echo "STEP4_ONLY_PREPARE=SUCCESS"

echo
echo "=== UPDATE STEP4-ONLY ==="

aws stepfunctions update-state-machine \
  --region "${AWS_REGION}" \
  --state-machine-arn "${STEP4_ONLY_STATE_MACHINE_ARN}" \
  --definition file:///tmp/research-step4-only-definition-updated.json \
  > /tmp/research-step4-only-update-result.json

echo "STEP4_ONLY_UPDATE_REQUEST=SUCCESS"

echo
echo "=== VERIFY STEP4-ONLY AFTER UPDATE ==="

aws stepfunctions describe-state-machine \
  --region "${AWS_REGION}" \
  --state-machine-arn "${STEP4_ONLY_STATE_MACHINE_ARN}" \
  --query 'definition' \
  --output text \
  > /tmp/research-step4-only-definition-after.json

AFTER_STEP4_ONLY_JOB_DEFINITION="$(
  jq -r \
    '.States.Step4_SubmitBacktestResearch.Parameters.JobDefinition // empty' \
    /tmp/research-step4-only-definition-after.json
)"

if [[ "${AFTER_STEP4_ONLY_JOB_DEFINITION}" != "${OPERATING_JOB_DEFINITION_ARN}" ]]; then
  echo "STEP4_ONLY_AFTER_CHECK_FAILED"
  echo "EXPECTED=${OPERATING_JOB_DEFINITION_ARN}"
  echo "ACTUAL=${AFTER_STEP4_ONLY_JOB_DEFINITION}"
  exit 64
fi

echo "STEP4_ONLY_JOB_DEFINITION=${AFTER_STEP4_ONLY_JOB_DEFINITION}"
echo "STEP4_ONLY_AFTER_CHECK=SUCCESS"

echo
echo "=== OPERATING PROMOTION RESULT ==="

echo "OPERATING_PREVIOUS_REVISION=${BASELINE_REVISION}"
echo "OPERATING_NEW_REVISION=${OPERATING_REVISION}"
echo "OPERATING_STRATEGY_CONFIG_VERSION=${BASELINE_CONFIG_VERSION}"
echo "OPERATING_ARTIFACT_CHANGED=YES"
echo "STRATEGY_CONFIG_CHANGED=NO"
echo "PRODUCTION_OPERATING_PROMOTION=SUCCESS"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "operating_revision=${OPERATING_REVISION}"
    echo "operating_job_definition_arn=${OPERATING_JOB_DEFINITION_ARN}"
    echo "operating_strategy_config_version=${BASELINE_CONFIG_VERSION}"
  } >> "${GITHUB_OUTPUT}"
fi