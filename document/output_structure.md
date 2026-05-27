# Output Structure

이 문서는 미션 생성 후 어떤 파일이 어디에 저장되는지 설명합니다.

## Main Output Roots

| 경로 | 역할 |
|---|---|
| `outputs/profiles/v1/` | 기준 job profile JSON |
| `outputs/pilot/v1/runs/{run_id}/` | 한 번의 파일럿 실행 산출물 |
| `outputs/ui/v1/runs/{run_id}/mission_ui.html` | 검토자용 QA HTML |
| `outputs/ui/v1/runs/{run_id}/mission_learner.html` | 학습자용 HTML |

## Current Reference Run

현재 커밋된 기준 run은 다음입니다.

```text
pilot_v1_20260527_032732_complete
```

경로:

```text
outputs/pilot/v1/runs/pilot_v1_20260527_032732_complete/
outputs/ui/v1/runs/pilot_v1_20260527_032732_complete/mission_ui.html
outputs/ui/v1/runs/pilot_v1_20260527_032732_complete/mission_learner.html
```

이 run은 7개 직무 x 3개 난이도 = 21개 `mission_output.json`을 포함합니다.

## What Is a Run ID?

`run_id`는 한 번의 실행 결과를 구분하는 이름입니다.

예시:

```text
pilot_v1_20260527_032732_complete
```

같은 `run_id`는 `outputs/pilot`과 `outputs/ui`에서 서로 매칭됩니다.

```text
outputs/pilot/v1/runs/{run_id}/
outputs/ui/v1/runs/{run_id}/
```

## Pilot Run Layout

```text
outputs/pilot/v1/runs/{run_id}/
  pilot_config.json
  pilot_summary.json
  artifact_index.json
  _failed/failure_index.json
  profiles/{job_cd}.json
  human_review/
    pilot_review.md
    pilot_review.json
  jobs/{job_cd}/{difficulty}/
    decision_selector_input.json
    decision_selector_call_result.json
    decision_selector_result.json
    decision_selector_validation.json
    system_decisions.json
    schema_constraints.json
    job_practice_sheet_background.json
    llm_input_package.json
    llm_call_result_attempt_0.json
    mission_draft_attempt_0.json
    validator_result_attempt_0.json
    repair_request_attempt_1.json
    llm_call_result_attempt_1.json
    mission_draft_attempt_1.json
    validator_result_attempt_1.json
    mission_output.json
    run_status.json
```

항상 모든 파일이 생기는 것은 아닙니다.

- repair가 없으면 `repair_request_attempt_1.json`, `llm_call_result_attempt_1.json`, `mission_draft_attempt_1.json`, `validator_result_attempt_1.json`은 없습니다.
- `--mission-seed`를 쓰는 legacy 경로에서는 `mission_seed.json`, `job_practice_profile.json`이 생길 수 있습니다.
- 기본 practice sheet background 모드에서는 `mission_seed.json`이 없습니다.

## Files to Check First

| 파일 | 용도 |
|---|---|
| `pilot_summary.json` | 전체 target 수, 저장/실패 개수, repair 개수, token 사용량 |
| `artifact_index.json` | 각 job/difficulty별 산출물 경로 |
| `_failed/failure_index.json` | 실패한 target과 실패 코드 |
| `jobs/{job_cd}/{difficulty}/mission_output.json` | 최종 생성 미션 |
| `jobs/{job_cd}/{difficulty}/run_status.json` | 개별 target의 최종 상태 |
| `jobs/{job_cd}/{difficulty}/validator_result_attempt_N.json` | validator 검사 결과 |
| `jobs/{job_cd}/{difficulty}/repair_request_attempt_1.json` | repair 발생 시 LLM에 전달된 실패 이유 |
| `outputs/ui/v1/runs/{run_id}/mission_ui.html` | 검토자용 QA 화면 |
| `outputs/ui/v1/runs/{run_id}/mission_learner.html` | 학습자용 화면 |

## Final Mission File

최종 미션 JSON은 다음 위치에 있습니다.

```text
outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/mission_output.json
```

예시:

```text
outputs/pilot/v1/runs/pilot_v1_20260527_032732_complete/jobs/K000001080/normal/mission_output.json
```

이 파일에는 미션 시나리오, 제공 자료, task, 제출 형식, 평가 기준, validator가 만든 evidence chain과 reliability가 들어 있습니다.

## UI Outputs

HTML export는 `ui_exporter.py`에서 수행합니다.

```powershell
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS --view review
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS --view learner
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS --view both
```

| view | 생성 파일 | 특징 |
|---|---|---|
| `review` | `mission_ui.html` | 실패 slot, reliability, evidence, repair 등 QA 정보 표시 |
| `learner` | `mission_learner.html` | saved mission만 표시하고 내부 ID/evidence/reliability 숨김 |
| `both` | 두 파일 모두 | 검토와 시연을 함께 준비할 때 사용 |

## Published Outputs

public GitHub에는 공개 기준으로 정한 HTML과 그 HTML에 대응되는 원본 산출물만 선별해 올립니다.

포함 기준:

- `outputs/ui/v1/runs/{run_id}/mission_ui.html`
- `outputs/ui/v1/runs/{run_id}/mission_learner.html`
- 같은 `run_id`의 `outputs/pilot/v1/runs/{run_id}/`

제외 기준:

- 기준 UI와 매칭되지 않는 임시 run
- `outputs/_test_tmp/`
- raw request/response dump
- `.tmp`, `.bak`, 로그 파일
