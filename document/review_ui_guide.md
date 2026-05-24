# Review UI Guide

검수 UI는 생성된 미션을 브라우저에서 확인하기 위한 단일 HTML 파일입니다. 코드를 읽지 않아도 직업별 미션, 제공 자료, task, 평가 기준을 살펴볼 수 있게 만든 화면입니다.

## Location

```text
outputs/ui/v1/runs/{run_id}/mission_ui.html
```

GitHub에 올라간 HTML은 브라우저에서 직접 열어 확인할 수 있습니다.

## Export a New Review UI

새로 생성한 pilot run을 HTML로 내보내려면 콘솔에 출력된 run id를 사용합니다.

```powershell
$env:PYTHONPATH="src"
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS
```

특정 pilot run 폴더와 UI 출력 폴더를 직접 지정할 수도 있습니다.

```powershell
$env:PYTHONPATH="src"
python -m mission_generation.ui_exporter --pilot-run-dir outputs/pilot/v1/runs/pilot_v1_YYYYMMDD_HHMMSS --ui-output-dir outputs/ui/v1/runs/pilot_v1_YYYYMMDD_HHMMSS
```

## What to Review

검수자는 HTML에서 다음 내용을 우선 확인합니다.

| 항목 | 확인 내용 |
|---|---|
| 직업/난이도 선택 | 의도한 job과 difficulty가 표시되는지 |
| 미션 시나리오 | 직업 맥락과 난이도가 자연스러운지 |
| 제공 자료 | 표, 차트, 메모, 이메일 등이 과제와 연결되는지 |
| task | 사용자가 답할 수 있는 지시문인지 |
| 평가 기준 | task와 채점 기준이 대응되는지 |
| 오류 표시 | 실패 target과 실패 이유가 확인되는지 |

## Relationship to `mission_output.json`

HTML은 검수 편의를 위한 화면입니다. 최종 데이터 원본은 `mission_output.json`입니다.

UI에서 이상이 보이면 같은 run의 원본 JSON을 함께 확인합니다.

```text
outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/mission_output.json
```

## Typical Review Flow

1. `mission_ui.html`을 브라우저에서 엽니다.
2. 직업과 난이도를 선택합니다.
3. 제공 자료가 task를 풀기에 충분한지 확인합니다.
4. task가 너무 모호하거나 정답을 유도하지 않는지 확인합니다.
5. 평가 기준이 task와 연결되는지 확인합니다.
6. 문제가 있으면 같은 run의 `mission_output.json`을 열어 원본 구조를 확인합니다.

