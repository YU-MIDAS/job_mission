# Review and Learner UI Guide

HTML exporter는 같은 pilot run에서 두 종류의 단일 HTML 파일을 만들 수 있습니다.

| 파일 | 용도 |
|---|---|
| `mission_ui.html` | 검토자용 QA 화면 |
| `mission_learner.html` | 학습자용 정제 화면 |

## Location

```text
outputs/ui/v1/runs/{run_id}/mission_ui.html
outputs/ui/v1/runs/{run_id}/mission_learner.html
```

현재 기준 run:

```text
outputs/ui/v1/runs/pilot_v1_20260527_032732_complete/
```

## Export HTML

기본값은 검토자용 `mission_ui.html`만 생성합니다.

```powershell
$env:PYTHONPATH="src"
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS
```

학습자용만 생성:

```powershell
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS --view learner
```

둘 다 생성:

```powershell
python -m mission_generation.ui_exporter --run-id pilot_v1_YYYYMMDD_HHMMSS --view both
```

특정 폴더를 직접 지정할 수도 있습니다.

```powershell
python -m mission_generation.ui_exporter --pilot-run-dir outputs/pilot/v1/runs/pilot_v1_YYYYMMDD_HHMMSS --ui-output-dir outputs/ui/v1/runs/pilot_v1_YYYYMMDD_HHMMSS --view both
```

## Review UI

검토자용 `mission_ui.html`은 QA를 위해 내부 정보를 많이 보여줍니다.

확인할 항목:

| 항목 | 확인 내용 |
|---|---|
| run summary | saved/failed, repair, reliability, API 호출 상태 |
| 직업/난이도 선택 | 의도한 job과 difficulty가 모두 표시되는지 |
| 실패 slot | 실패한 target과 실패 이유가 보이는지 |
| 미션 시나리오 | 직무 맥락과 난이도가 자연스러운지 |
| 제공 자료 | task를 풀기에 충분한 자료인지 |
| task | 자료와 instruction이 맞물리는지 |
| evidence | material evidence source가 실제 profile evidence와 연결되는지 |
| evaluation | rubric과 expected insight가 task와 대응되는지 |

## Learner UI

학습자용 `mission_learner.html`은 실제 학습 화면에 가깝게 내부 필드를 숨깁니다.

숨기는 정보:

- `mission_id`, `task_id`, raw material id
- `source_ref`, `evidence_source`, `evidence_chain`
- `reliability`, `repair_count`, `warning_count`
- `expected_action`
- failed/missing slot
- API 상태와 run summary

보여주는 정보:

- 시나리오
- 용어 정리 카드
- 제공 자료
- 수행 과제
- 답변 입력란과 글자 수
- 제한 시간
- 제출 형식
- 간단 평가 기준

## Mission Picker

학습자용 화면의 미션 선택 영역은 직무별 그룹으로 묶입니다. 각 직무 그룹 아래에 쉬움/보통/어려움 미션이 모여 보입니다.

예시:

```text
광고·홍보·마케팅전문가
  - 쉬움
  - 보통
  - 어려움
```

모바일에서는 미션을 선택하면 상세 영역으로 자동 스크롤합니다.

## Glossary Display

`mission.scenario.glossary` 항목은 시나리오 본문과 분리되어 `용어 정리` 카드로 표시됩니다.

과거 산출물 호환을 위해 UI exporter는 본문 끝의 `용어 설명:` 패턴도 가능한 범위에서 glossary 카드로 분리합니다. 하지만 새로 생성되는 미션은 schema의 `glossary` 필드를 사용하는 것이 기준입니다.

## Relationship to `mission_output.json`

HTML은 검수와 시연을 위한 화면입니다. 최종 데이터 원본은 항상 `mission_output.json`입니다.

```text
outputs/pilot/v1/runs/{run_id}/jobs/{job_cd}/{difficulty}/mission_output.json
```

UI에서 이상이 보이면 같은 run의 원본 JSON을 함께 확인합니다.
