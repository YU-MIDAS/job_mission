# Data Requirements

이 프로젝트를 새 환경에서 실행하려면 GitHub에 포함되지 않는 로컬 데이터와 API key를 직접 준비해야 합니다.

## Required Local Data

원천 XML은 다음 위치에 둡니다.

```text
data/api_raw/{job_cd}/
  dtlGb_2.xml
  dtlGb_5.xml
  dtlGb_7.xml
  dtlGb_3.xml
```

예시:

```text
data/api_raw/
  K000000997/
    dtlGb_2.xml
    dtlGb_5.xml
    dtlGb_7.xml
    dtlGb_3.xml
```

필수 파일:

| 파일 | 용도 |
|---|---|
| `dtlGb_2.xml` | 직업 상세 정보 |
| `dtlGb_5.xml` | 업무수행능력, 지식 등 생성 근거 |
| `dtlGb_7.xml` | 업무환경 등 생성 근거 |

선택 파일:

| 파일 | 용도 |
|---|---|
| `dtlGb_3.xml` | 추가 직업 정보가 있을 때 사용 |

현재 실행 경로에서는 `data/k-means`, `data/raw`, 대용량 CSV 파일이 없어도 됩니다.

## Why Data Is Not Included

`data/`는 `.gitignore` 대상입니다. 원천 XML이나 대용량 데이터는 공개 저장소에 올리지 않고, 실행하는 사람이 로컬에서 준비하는 것을 기준으로 합니다.

## API Key

실제 OpenAI API를 호출하려면 `OPENAI_API_KEY`가 필요합니다.

PowerShell 환경변수:

```powershell
$env:OPENAI_API_KEY="본인_API_KEY"
```

또는 프로젝트 루트의 `.env.local`:

```text
OPENAI_API_KEY=본인_API_KEY
```

`.env.local`, `.env`, `.env.*`는 GitHub에 올리지 않습니다.

## Python Import Path

`pyproject.toml`이나 `requirements.txt`는 아직 없으므로 실행 전에 `src`를 Python import 경로에 추가합니다.

```powershell
$env:PYTHONPATH="src"
```

## Sanity Check

데이터 없이도 mock 실행으로 파이프라인 구조를 확인할 수 있습니다.

```powershell
python -m mission_generation.pilot_runner --mock --jobs K000000997 --difficulties normal --concurrency 1
```

실제 API 실행 전에는 테스트를 먼저 돌리는 것을 권장합니다.

```powershell
python -B -m unittest discover -s tests
```

