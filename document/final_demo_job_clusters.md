# 최종 시연 직무 목록

이 문서는 최종 시연과 `pilot_v1_20260527_032732_complete` 기준 run에서 사용한 직무를 정리합니다.

## Complete Run Target

최종 기준 run은 7개 직무 x 3개 난이도 = 21개 미션으로 구성되어 있습니다.

```text
pilot_v1_20260527_032732_complete
```

| job_cd | 직업 | 군집 | complete run 포함 |
|---|---|---|---|
| `K000000872` | 광고·홍보·마케팅전문가 | C2 | 예 |
| `K000000997` | 상품기획자 | C2 | 예 |
| `K000001080` | 데이터분석가(빅데이터분석가) | C3 | 예 |
| `K000001179` | 투자분석가 | C2 | 예 |
| `K000001196` | 인사·교육·훈련사무원 | C2 | 예 |
| `K000001222` | 방송기자 | C2 | 예 |
| `K000007519` | 보험상품개발자 | C2 | 예 |

## Additional Candidate Jobs

초기 후보에는 있었지만, 현재 complete run의 21개 미션에는 포함하지 않은 직무입니다.

| job_cd | 직업 | 군집 | complete run 포함 |
|---|---|---|---|
| `K000000890` | UX·UI디자이너 | C3 | 아니오 |
| `K000001106` | 웹개발자 | C3 | 아니오 |
| `K000001138` | 방송연출가 | C3 | 아니오 |
| `K000001176` | 응용소프트웨어 개발자 | C3 | 아니오 |

## Output Locations

미션 JSON:

```text
outputs/pilot/v1/runs/pilot_v1_20260527_032732_complete/jobs/{job_cd}/{difficulty}/mission_output.json
```

HTML:

```text
outputs/ui/v1/runs/pilot_v1_20260527_032732_complete/mission_ui.html
outputs/ui/v1/runs/pilot_v1_20260527_032732_complete/mission_learner.html
```

## Count

| 구분 | 직무 수 | 난이도 수 | 미션 수 |
|---|---:|---:|---:|
| complete run 포함 | 7 | 3 | 21 |
| 추가 후보 | 4 | - | - |
| 전체 후보 | 11 | - | - |
