#!/usr/bin/env bash

set -euo pipefail


SOURCE_SHA="${1:?SOURCE_SHA is required}"
AWS_REGION="${2:?AWS_REGION is required}"
ECR_REPOSITORY_NAME="${3:?ECR_REPOSITORY_NAME is required}"
CANDIDATE_JOB_DEFINITION_NAME="${4:?CANDIDATE_JOB_DEFINITION_NAME is required}"
CANDIDATE_JOB_QUEUE="${5:?CANDIDATE_JOB_QUEUE is required}"
GITHUB_RUN_ID_VALUE="${6:?GITHUB_RUN_ID is required}"
STRATEGY_CONFIG_VERSION="${7:?STRATEGY_CONFIG_VERSION is required}"

CANDIDATE_MEMORY="4096"


if [[ ! "${SOURCE_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "SOURCE_SHA_INVALID=${SOURCE_SHA}"
  exit 60
fi

if [[ ! "${STRATEGY_CONFIG_VERSION}" =~ ^RSCFG-[0-9]{4}$ ]]; then
  echo "STRATEGY_CONFIG_VERSION_INVALID=${STRATEGY_CONFIG_VERSION}"
  exit 61
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
  exit 62
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
  exit 63
fi

IMAGE_URI="$(
  printf '%s.dkr.ecr.%s.amazonaws.com/%s@%s' \
    "${AWS_ACCOUNT_ID}" \
    "${AWS_REGION}" \
    "${ECR_REPOSITORY_NAME}" \
    "${IMAGE_DIGEST}"
)"

echo "SOURCE_SHA=${SOURCE_SHA}"
echo "SHORT_SHA=${SHORT_SHA}"
echo "IMAGE_DIGEST_RESOLVED=YES"
echo "ECR_ARTIFACT_IDENTITY=SUCCESS"


echo
echo "=== RESOLVE CANDIDATE BASELINE ==="

aws batch describe-job-definitions \
  --region "${AWS_REGION}" \
  --job-definition-name "${CANDIDATE_JOB_DEFINITION_NAME}" \
  --status ACTIVE \
  --output json \
  > /tmp/research-candidate-definitions.json

CANDIDATE_COUNT="$(
  jq '.jobDefinitions | length' \
    /tmp/research-candidate-definitions.json
)"

if [[ "${CANDIDATE_COUNT}" -lt 1 ]]; then
  echo "ACTIVE_CANDIDATE_JOB_DEFINITION_NOT_FOUND"
  exit 70
fi

jq '
  .jobDefinitions
  | sort_by(.revision)
  | reverse
  | .[0]
' /tmp/research-candidate-definitions.json \
  > /tmp/research-candidate-baseline.json

BASELINE_NAME="$(
  jq -r '.jobDefinitionName' \
    /tmp/research-candidate-baseline.json
)"

BASELINE_REVISION="$(
  jq -r '.revision' \
    /tmp/research-candidate-baseline.json
)"

BASELINE_TYPE="$(
  jq -r '.type' \
    /tmp/research-candidate-baseline.json
)"

BASELINE_MEMORY="$(
  jq -r '
    .containerProperties.resourceRequirements[]
    | select(.type == "MEMORY")
    | .value
  ' /tmp/research-candidate-baseline.json
)"

BASELINE_VCPU="$(
  jq -r '
    .containerProperties.resourceRequirements[]
    | select(.type == "VCPU")
    | .value
  ' /tmp/research-candidate-baseline.json
)"

if [[ "${BASELINE_NAME}" != "${CANDIDATE_JOB_DEFINITION_NAME}" ]]; then
  echo "CANDIDATE_BASELINE_NAME_MISMATCH=${BASELINE_NAME}"
  exit 71
fi

if [[ "${BASELINE_TYPE}" != "container" ]]; then
  echo "CANDIDATE_BASELINE_TYPE_INVALID=${BASELINE_TYPE}"
  exit 72
fi

if ! jq -e '
  .platformCapabilities
  | index("FARGATE") != null
' /tmp/research-candidate-baseline.json >/dev/null; then
  echo "CANDIDATE_BASELINE_NOT_FARGATE"
  exit 73
fi

if ! jq -e '
  .containerProperties.command
  | index("--run-mode") != null
' /tmp/research-candidate-baseline.json >/dev/null; then
  echo "CANDIDATE_RUN_MODE_ARGUMENT_MISSING"
  exit 74
fi

if ! jq -e '
  .containerProperties.command
  | index("CANDIDATE") != null
' /tmp/research-candidate-baseline.json >/dev/null; then
  echo "CANDIDATE_RUN_MODE_VALUE_MISSING"
  exit 75
fi

if ! jq -e '
  .containerProperties.command
  | index("--strategy-config-version") != null
' /tmp/research-candidate-baseline.json >/dev/null; then
  echo "CANDIDATE_STRATEGY_CONFIG_ARGUMENT_MISSING"
  exit 76
fi

if ! jq -e '
  .containerProperties.command
  | index("--require-artifact-identity") != null
' /tmp/research-candidate-baseline.json >/dev/null; then
  echo "CANDIDATE_ARTIFACT_IDENTITY_ARGUMENT_MISSING"
  exit 77
fi

echo "CANDIDATE_BASELINE_REVISION=${BASELINE_REVISION}"
echo "CANDIDATE_BASELINE_VCPU=${BASELINE_VCPU}"
echo "CANDIDATE_BASELINE_MEMORY=${BASELINE_MEMORY}"
echo "CANDIDATE_TARGET_MEMORY=${CANDIDATE_MEMORY}"
echo "CANDIDATE_BASELINE_RUNTIME_CONTRACT=SUCCESS"


echo
echo "=== PREPARE CANDIDATE JOB DEFINITION ==="

jq \
  --arg image_uri "${IMAGE_URI}" \
  --arg source_sha "${SOURCE_SHA}" \
  --arg image_digest "${IMAGE_DIGEST}" \
  --arg candidate_memory "${CANDIDATE_MEMORY}" \
  --arg strategy_config_version "${STRATEGY_CONFIG_VERSION}" \
  '
  {
    jobDefinitionName: .jobDefinitionName,
    type: .type,

    containerProperties:
      (
        .containerProperties

        | .image = $image_uri

        | .command =
          (
            .command as $cmd
            | ($cmd | index("--strategy-config-version")) as $i
            | if $i == null
              then error("CANDIDATE_STRATEGY_CONFIG_ARGUMENT_MISSING")
              else
                $cmd
                | .[$i + 1] = $strategy_config_version
              end
          )

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

        | .resourceRequirements =
          (
            (.resourceRequirements // [])
            | map(
                if .type == "MEMORY"
                then .value = $candidate_memory
                else .
                end
              )
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
  ' \
  /tmp/research-candidate-baseline.json \
  > /tmp/research-candidate-register.json


PREPARED_CONFIG_VERSION="$(
  jq -r '
    .containerProperties.command as $cmd
    | ($cmd | index("--strategy-config-version")) as $i
    | if $i == null then empty else $cmd[$i + 1] end
  ' /tmp/research-candidate-register.json
)"

PREPARED_IMAGE="$(
  jq -r '.containerProperties.image' \
    /tmp/research-candidate-register.json
)"

PREPARED_SOURCE_SHA="$(
  jq -r '
    .containerProperties.environment[]
    | select(.name == "RESEARCH_SOURCE_SHA")
    | .value
  ' /tmp/research-candidate-register.json
)"

PREPARED_IMAGE_DIGEST="$(
  jq -r '
    .containerProperties.environment[]
    | select(.name == "RESEARCH_IMAGE_DIGEST")
    | .value
  ' /tmp/research-candidate-register.json
)"

PREPARED_MEMORY="$(
  jq -r '
    .containerProperties.resourceRequirements[]
    | select(.type == "MEMORY")
    | .value
  ' /tmp/research-candidate-register.json
)"

PREPARED_VCPU="$(
  jq -r '
    .containerProperties.resourceRequirements[]
    | select(.type == "VCPU")
    | .value
  ' /tmp/research-candidate-register.json
)"

if [[ "${PREPARED_CONFIG_VERSION}" != "${STRATEGY_CONFIG_VERSION}" ]]; then
  echo "CANDIDATE_PREPARED_CONFIG_VERSION_MISMATCH"
  echo "EXPECTED=${STRATEGY_CONFIG_VERSION}"
  echo "ACTUAL=${PREPARED_CONFIG_VERSION}"
  exit 79
fi

if [[ "${PREPARED_IMAGE}" != "${IMAGE_URI}" ]]; then
  echo "CANDIDATE_PREPARED_IMAGE_MISMATCH"
  exit 80
fi

if [[ "${PREPARED_SOURCE_SHA}" != "${SOURCE_SHA}" ]]; then
  echo "CANDIDATE_PREPARED_SOURCE_SHA_MISMATCH"
  exit 81
fi

if [[ "${PREPARED_IMAGE_DIGEST}" != "${IMAGE_DIGEST}" ]]; then
  echo "CANDIDATE_PREPARED_IMAGE_DIGEST_MISMATCH"
  exit 82
fi

if [[ "${PREPARED_MEMORY}" != "${CANDIDATE_MEMORY}" ]]; then
  echo "CANDIDATE_PREPARED_MEMORY_MISMATCH=${PREPARED_MEMORY}"
  exit 83
fi

if [[ -z "${PREPARED_VCPU}" || "${PREPARED_VCPU}" == "null" ]]; then
  echo "CANDIDATE_PREPARED_VCPU_EMPTY"
  exit 84
fi

echo "CANDIDATE_RUNTIME_BASELINE_COPIED=SUCCESS"
echo "CANDIDATE_ARTIFACT_IDENTITY_INJECTED=SUCCESS"
echo "CANDIDATE_VCPU=${PREPARED_VCPU}"
echo "CANDIDATE_MEMORY=${PREPARED_MEMORY}"
echo "CANDIDATE_RUNTIME_RESOURCE_ALIGNMENT=SUCCESS"


echo
echo "=== REGISTER CANDIDATE JOB DEFINITION ==="

REGISTER_RESULT="$(
  aws batch register-job-definition \
    --region "${AWS_REGION}" \
    --cli-input-json file:///tmp/research-candidate-register.json
)"

CANDIDATE_JOB_DEFINITION_ARN="$(
  jq -r '.jobDefinitionArn' <<< "${REGISTER_RESULT}"
)"

CANDIDATE_REVISION="$(
  jq -r '.revision' <<< "${REGISTER_RESULT}"
)"

if [[ -z "${CANDIDATE_JOB_DEFINITION_ARN}" ||
      "${CANDIDATE_JOB_DEFINITION_ARN}" == "null" ]]; then
  echo "CANDIDATE_JOB_DEFINITION_ARN_EMPTY"
  exit 90
fi

if [[ ! "${CANDIDATE_REVISION}" =~ ^[0-9]+$ ]]; then
  echo "CANDIDATE_REVISION_INVALID=${CANDIDATE_REVISION}"
  exit 91
fi

echo "CANDIDATE_REVISION=${CANDIDATE_REVISION}"
echo "CANDIDATE_JOB_DEFINITION_REGISTRATION=SUCCESS"


echo
echo "=== VERIFY REGISTERED CANDIDATE ==="

CANDIDATE_JSON="$(
  aws batch describe-job-definitions \
    --region "${AWS_REGION}" \
    --job-definitions "${CANDIDATE_JOB_DEFINITION_ARN}" \
    --query 'jobDefinitions[0]' \
    --output json
)"

REGISTERED_CONFIG_VERSION="$(
  jq -r '
    .containerProperties.command as $cmd
    | ($cmd | index("--strategy-config-version")) as $i
    | if $i == null then empty else $cmd[$i + 1] end
  ' <<< "${CANDIDATE_JSON}"
)"

REGISTERED_IMAGE="$(
  jq -r '.containerProperties.image' \
    <<< "${CANDIDATE_JSON}"
)"

REGISTERED_SOURCE_SHA="$(
  jq -r '
    .containerProperties.environment[]
    | select(.name == "RESEARCH_SOURCE_SHA")
    | .value
  ' <<< "${CANDIDATE_JSON}"
)"

REGISTERED_IMAGE_DIGEST="$(
  jq -r '
    .containerProperties.environment[]
    | select(.name == "RESEARCH_IMAGE_DIGEST")
    | .value
  ' <<< "${CANDIDATE_JSON}"
)"

REGISTERED_MEMORY="$(
  jq -r '
    .containerProperties.resourceRequirements[]
    | select(.type == "MEMORY")
    | .value
  ' <<< "${CANDIDATE_JSON}"
)"

REGISTERED_VCPU="$(
  jq -r '
    .containerProperties.resourceRequirements[]
    | select(.type == "VCPU")
    | .value
  ' <<< "${CANDIDATE_JSON}"
)"

if [[ "${REGISTERED_CONFIG_VERSION}" != "${STRATEGY_CONFIG_VERSION}" ]]; then
  echo "REGISTERED_CANDIDATE_CONFIG_VERSION_MISMATCH"
  echo "EXPECTED=${STRATEGY_CONFIG_VERSION}"
  echo "ACTUAL=${REGISTERED_CONFIG_VERSION}"
  exit 99
fi

if [[ "${REGISTERED_IMAGE}" != "${IMAGE_URI}" ]]; then
  echo "REGISTERED_CANDIDATE_IMAGE_MISMATCH"
  exit 100
fi

if [[ "${REGISTERED_SOURCE_SHA}" != "${SOURCE_SHA}" ]]; then
  echo "REGISTERED_CANDIDATE_SOURCE_SHA_MISMATCH"
  exit 101
fi

if [[ "${REGISTERED_IMAGE_DIGEST}" != "${IMAGE_DIGEST}" ]]; then
  echo "REGISTERED_CANDIDATE_IMAGE_DIGEST_MISMATCH"
  exit 102
fi

if [[ "${REGISTERED_MEMORY}" != "${CANDIDATE_MEMORY}" ]]; then
  echo "REGISTERED_CANDIDATE_MEMORY_MISMATCH=${REGISTERED_MEMORY}"
  exit 103
fi

if [[ -z "${REGISTERED_VCPU}" || "${REGISTERED_VCPU}" == "null" ]]; then
  echo "REGISTERED_CANDIDATE_VCPU_EMPTY"
  exit 104
fi

echo "REGISTERED_CANDIDATE_CONFIG_VERSION=${REGISTERED_CONFIG_VERSION}"
echo "REGISTERED_CANDIDATE_CONFIG_VERSION=SUCCESS"
echo "REGISTERED_CANDIDATE_ARTIFACT_IDENTITY=SUCCESS"
echo "REGISTERED_CANDIDATE_VCPU=${REGISTERED_VCPU}"
echo "REGISTERED_CANDIDATE_MEMORY=${REGISTERED_MEMORY}"
echo "REGISTERED_CANDIDATE_RUNTIME_RESOURCE=SUCCESS"
echo "CANDIDATE_JOB_DEFINITION_VERIFY=SUCCESS"


echo
echo "=== SUBMIT RESEARCH CANDIDATE ==="

JOB_NAME="research-candidate-${SHORT_SHA}-${GITHUB_RUN_ID_VALUE}"

SUBMIT_RESULT="$(
  aws batch submit-job \
    --region "${AWS_REGION}" \
    --job-name "${JOB_NAME}" \
    --job-queue "${CANDIDATE_JOB_QUEUE}" \
    --job-definition "${CANDIDATE_JOB_DEFINITION_ARN}"
)"

JOB_ID="$(
  jq -r '.jobId' <<< "${SUBMIT_RESULT}"
)"

if [[ -z "${JOB_ID}" || "${JOB_ID}" == "null" ]]; then
  echo "CANDIDATE_JOB_ID_EMPTY"
  exit 110
fi

echo "CANDIDATE_JOB_NAME=${JOB_NAME}"
echo "CANDIDATE_JOB_SUBMIT=SUCCESS"


echo
echo "=== WAIT FOR RESEARCH CANDIDATE ==="

while true; do
  JOB_JSON="$(
    aws batch describe-jobs \
      --region "${AWS_REGION}" \
      --jobs "${JOB_ID}" \
      --query 'jobs[0]' \
      --output json
  )"

  JOB_STATUS="$(
    jq -r '.status // empty' \
      <<< "${JOB_JSON}"
  )"

  if [[ -z "${JOB_STATUS}" ]]; then
    echo "CANDIDATE_JOB_STATUS_EMPTY"
    exit 120
  fi

  echo "CANDIDATE_JOB_STATUS=${JOB_STATUS}"

  if [[ "${JOB_STATUS}" == "SUCCEEDED" ]]; then
    break
  fi

  if [[ "${JOB_STATUS}" == "FAILED" ]]; then
    STATUS_REASON="$(
      jq -r '.statusReason // "UNRESOLVED"' \
        <<< "${JOB_JSON}"
    )"

    CONTAINER_REASON="$(
      jq -r '.container.reason // "UNRESOLVED"' \
        <<< "${JOB_JSON}"
    )"

    FAILED_EXIT_CODE="$(
      jq -r '.container.exitCode // "UNRESOLVED"' \
        <<< "${JOB_JSON}"
    )"

    LOG_STREAM="$(
      jq -r '.container.logStreamName // "UNRESOLVED"' \
        <<< "${JOB_JSON}"
    )"

    echo "CANDIDATE_JOB_RESULT=FAILED"
    echo "CANDIDATE_JOB_STATUS_REASON=${STATUS_REASON}"
    echo "CANDIDATE_CONTAINER_REASON=${CONTAINER_REASON}"
    echo "CANDIDATE_CONTAINER_EXIT_CODE=${FAILED_EXIT_CODE}"
    echo "CANDIDATE_LOG_STREAM=${LOG_STREAM}"

    exit 121
  fi

  sleep 15
done


JOB_JSON="$(
  aws batch describe-jobs \
    --region "${AWS_REGION}" \
    --jobs "${JOB_ID}" \
    --query 'jobs[0]' \
    --output json
)"

EXIT_CODE="$(
  jq -r '.container.exitCode // empty' \
    <<< "${JOB_JSON}"
)"

RUN_JOB_DEFINITION="$(
  jq -r '.jobDefinition' \
    <<< "${JOB_JSON}"
)"

RUN_CONTAINER_MEMORY="$(
  jq -r '
    .container.resourceRequirements[]?
    | select(.type == "MEMORY")
    | .value
  ' <<< "${JOB_JSON}"
)"

if [[ -z "${EXIT_CODE}" ]]; then
  echo "CANDIDATE_CONTAINER_EXIT_CODE_EMPTY"
  exit 122
fi

if [[ "${EXIT_CODE}" != "0" ]]; then
  echo "CANDIDATE_CONTAINER_EXIT_CODE=${EXIT_CODE}"
  exit 123
fi

if [[ "${RUN_JOB_DEFINITION}" != "${CANDIDATE_JOB_DEFINITION_ARN}" ]]; then
  echo "CANDIDATE_RUNTIME_JOB_DEFINITION_MISMATCH"
  exit 124
fi

echo "CANDIDATE_RUNTIME_MEMORY=${RUN_CONTAINER_MEMORY:-UNRESOLVED}"
echo "CANDIDATE_CONTAINER_EXIT_CODE=${EXIT_CODE}"
echo "CANDIDATE_BATCH_RESULT=SUCCEEDED"
echo "RESEARCH_CANDIDATE_VERIFIED=SUCCESS"


if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "candidate_revision=${CANDIDATE_REVISION}"
    echo "candidate_job_name=${JOB_NAME}"
    echo "candidate_exit_code=${EXIT_CODE}"
  } >> "${GITHUB_OUTPUT}"
fi