# Output Structure

이 문서는 미션 생성 후 어떤 파일이 어디에 저장되는지 설명합니다. 생성된 결과를 찾고 싶다면 이 문서를 보면 됩니다.

## Main Output Roots

| 경로 | 역할 |
|---|---|
| `outputs/profiles/v1/` | 기준 job profile JSON |
| `outputs/pilot/v1/runs/{run_id}/` | 한 번의 파일럿 실행 산출물 |
| `outputs/ui/v1/runs/{run_id}/mission_ui.html` | 브라우저 검수용 HTML |

## What Is a Run ID?

`run_id`는 한 번의 실행 결과를 구분하는 이름입니다.

예시:

```text
pilot_v1_20260524_224708
```

같은 `run_id`는 `outputs/pilot`과 `outputs/ui`에서 서로 매칭됩니다.

```text
outputs/pilot/v1/runs/pilot_v1_20260524_224708/
outputs/ui/v1/runs/pilot_v1_20260524_224708/mission_ui.html
```

## Pilot Run Layout

```text
outputs/pilot/v1/runs/{run_id}/
  pilot_config.json
  pilot_summary.json
  artifact_index.json
  _failed/failure_index.json
  profiles/{job_cd}.json
  jobs/{job_cd}/{difficulty}/
    system_decisions.json
    schema_constraints.json
    llm_input_package.json
    llm_call_result_attempt_0.json
    mission_draft_attempt_0.json
    validator_result_attempt_0.json
    mission_output.json
    run_status.json
  human_review/pilot_review.md
```

## Files to Check First

| 파일 | 용도 |
|---|---|
| `pilot_summary.json` | 전체 성공/실패, API 호출 여부, 토큰 사용량 |
| `artifact_index.json` | 각 미션 산출물 경로 |
| `_failed/failure_index.json` | 실패한 target과 실패 코드 |
| `mission_output.json` | 최종 생성 미션 |
| `mission_ui.html` | 사람이 보는 검수 화면 |

## Final Mission File

최종 미션 JSON은 다음 위치에 있습니다.

```text
outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/mission_output.json
```

예시:

```text
outputs/pilot/v1/runs/pilot_v1_20260524_224708/jobs/K000000997/normal/mission_output.json
```

각 JSON 파일의 필드 의미는 `document/json_field_reference.md`에서 확인할 수 있습니다.

## Published Outputs

public GitHub에는 검수용 HTML과 그 HTML에 대응되는 원본 산출물만 선별해 올립니다.

포함 기준:

- `outputs/ui/v1/runs/{run_id}/mission_ui.html`이 있는 run
- 같은 `run_id`를 가진 `outputs/pilot/v1/runs/{run_id}/`
- 검수 UI 해석에 필요한 `outputs/profiles/v1/*.json`

제외 기준:

- UI와 매칭되지 않는 임시 run
- `outputs/_test_tmp/`
- raw request/response dump
- `.tmp`, `.bak`, 로그 파일
