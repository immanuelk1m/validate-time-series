# 동봉 실행기

목차: 환경 · Protocol 준비 · 평가 계획 동결 · 기준선 생성 · 다른 모델의 원장 제출 · 채점 · 최종 평가 · 명시적 한계

## 환경

Python 3.11 이상을 사용한다. 수치 계산은 NumPy, JSON schema 검사는 jsonschema를 사용하고 테스트는 표준 라이브러리 unittest로 실행한다. GPU, 모델 다운로드, 외부 API 호출은 기본 실행에 없다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
.venv/bin/python "$SKILL_DIR/scripts/test_validation.py"
.venv/bin/python "$SKILL_DIR/scripts/demo.py" --out ./ts-validation-demo
```

`$SKILL_DIR`는 이 스킬의 설치 디렉터리다. 프로젝트 데이터와 출력은 그 밖의 작업 디렉터리에 둔다. 기존 출력 디렉터리는 덮어쓰지 않으므로 재실행 때 새 경로를 지정한다.

## 1. Protocol 준비

`assets/protocol.example.json`을 작업 폴더에 복사해 수정한다. 이 파일의 시계열, 날짜, period=13, seed와 horizon은 합성 예제의 설정이다. 실제 원자재 자료에 그대로 적용하지 않는다.

모델별 candidate는 사전 등록한다. 같은 모델의 여러 설정은 구분되는 model_id를 갖는다. primary metric은 `mae`, `mse`, `rmse` 중 하나다. quantile 지표는 보조 산출물이다. 알려지지 않은 JSON 속성을 쓰면 schema 검사가 막으므로 추가 운영 명세는 별도 파일에 기록하고 audit evidence에서 연결한다.

## 2. 평가 계획 동결

```bash
.venv/bin/python "$SKILL_DIR/scripts/tsvalidate.py" lock \
  --protocol ./protocol.json --data ./target.csv --out ./runs/v1/plan
```

데이터는 다음 세 컬럼만 사용한다.

```csv
series_id,timestamp,value
copper,2024-01-07T00:00:00Z,100.0
copper,2024-01-14T00:00:00Z,101.0
```

위 두 행은 형식 설명용이며 실제 구리 가격이 아니다. 한 시계열에서 같은 timestamp는 한 번만 나타나야 한다.

계획에는 모델용 일정 `origins.jsonl`, 평가 전용 정답 `expected.jsonl`, 공통 경계 제외 기록과 `lock.json`이 생성된다. **expected 원장을 adapter에 전달하지 않는다.** scorer는 별도 프로세스에서 실행하는 것이 원칙이다.

## 3. 기준선 생성

```bash
.venv/bin/python "$SKILL_DIR/scripts/tsvalidate.py" baseline \
  --plan ./runs/v1/plan --data ./target.csv --method naive --out ./runs/v1/naive
.venv/bin/python "$SKILL_DIR/scripts/tsvalidate.py" baseline \
  --plan ./runs/v1/plan --data ./target.csv --method drift --out ./runs/v1/drift
.venv/bin/python "$SKILL_DIR/scripts/tsvalidate.py" baseline \
  --plan ./runs/v1/plan --data ./target.csv --method seasonal-naive --out ./runs/v1/seasonal-naive
```

builtin은 `information_set=target_history_only`, `learning_regime=from_scratch`, `refit_policy=each_origin`, 빈 quantile grid가 필요하다. 명세가 다르면 자동으로 맞춰 실행하지 않고 거부한다.

baseline의 training_seconds=0은 파라미터 최적화 학습을 수행하지 않는다는 뜻이다. inference_seconds는 baseline 산술 계산만 측정하며 파일 입출력을 포함하지 않는다. 다른 실행기의 end-to-end 시간과 그대로 비교하지 않는다.

## 4. 다른 모델의 원장 제출

각 실행 폴더에 `run.json`과 `forecasts.jsonl`을 저장한다. `assets/run.schema.json`이 manifest 형식이다. `run_id`는 실행 식별자, `model_spec.model_id`는 protocol에 등록된 후보 식별자다.

manifest에는 protocol/data hash, track, model 버전·코드 hash·설정, 감사 상태·증빙, 사전학습 중복 상태와 실행시간을 넣는다. 최종 모델 명세에는 checkpoint, dependency lock, feature pipeline, HPO 결과, ensemble/calibration 설정까지 config에 포함해 함께 동결한다. 환경이 바뀌면 같은 모델 버전으로 가장하지 않는다.

forecast 한 행의 형식은 다음과 같다. 수치와 날짜는 설명용이다.

```json
{"series_id":"copper","origin":"2024-01-14T00:00:00Z","target_time":"2024-01-21T00:00:00Z","horizon":1,"seed":0,"status":"ok","point":101.5,"quantiles":{},"fit_cutoff":"2024-01-14T00:00:00Z","preprocess_cutoff":"2024-01-14T00:00:00Z"}
```

`fit_cutoff`와 `preprocess_cutoff`는 각각 학습과 전처리에 사용한 시간 범위의 상한이며 forecast origin을 넘을 수 없다.

확률 track이면 `quantiles`를 `{"0.1":95.0,"0.5":101.5,"0.9":109.0}`처럼 넣는다. 요청한 grid와 정확히 일치해야 한다. median track에서는 point가 q0.5와 같아야 한다.

실패한 예측도 같은 식별 키를 유지하고 `status=failed`, `error`를 남긴다. 한 후보는 정해진 seed를 모두 포함하는 원장 하나를 제출한다. 미제출한 후보도 리더보드에서 사라지지 않는다. Schema 자체가 잘못된 manifest나 중복 candidate 제출은 전체 명령을 막고, candidate 내부의 예측 오류는 해당 후보를 INVALID로 남긴다.

## 5. 채점

```bash
.venv/bin/python "$SKILL_DIR/scripts/tsvalidate.py" score \
  --plan ./runs/v1/plan \
  --runs ./runs/v1/naive/run.json ./runs/v1/drift/run.json ./runs/v1/seasonal-naive/run.json \
  --out ./runs/v1/evaluation
```

| 파일 | 내용 |
|---|---|
| `leaderboard.csv` | 같은 track의 macro skill·순위, 표본 coverage, eligibility와 진단 지표 |
| `horizon_metrics.csv` | series×horizon별 point/scaled/확률 지표 |
| `fold_metrics.csv` | 연속 origin 블록별 지표 |
| `regime_metrics.csv` | 정의한 국면별 지표. 표본이 없으면 행이 없음 |
| `statistical_tests.csv` | 켜 둔 경우에만 DM-HAC·CI·Holm 결과. 기본은 빈 파일 |
| `losses.jsonl` | 성공 예측의 원래 키, 값과 손실. 실패 건수는 audit/원본 forecast 참조 |
| `audit.json` | 예상·유효 표본 수, 후보별 실패 사유 |
| `summary.json` | 실행 설정, 결과와 해석 한계 |
| `provenance.json` | 입력 manifest, 예측 파일, evaluator 코드와 계획의 hash |

coverage 열은 제출/성공 표본 비율이다. Prediction interval coverage와 구분한다. INVALID나 INCOMPLETE 후보의 성공 표본 지표는 진단용이며 순위와 macro skill은 비워 둔다. 다른 track 간 전체 1등을 자동 선정하지 않는다.

## 최종 평가

개발 평가 뒤 승인된 model_spec의 canonical JSON SHA-256을 `final_selection.model_spec_hashes`에 넣는다. 코드의 `digest()`가 사용하는 규칙은 UTF-8, sort_keys=true, ensure_ascii=false, separators=(",",":")이다. 테스트를 보며 hash 목록을 다시 고르면 안 된다.

새 최종 protocol에서 `phase=final`, 날짜·후보·승인 기록을 설정하고 다시 lock한다. final에서 실제 실행할 후보만 등록하고 필수 기준선도 그 명세를 승인한다. 해당 plan hash로 실행한 예측 원장을 제출한다. 기존 개발 점수만 복사해 최종 결과로 바꾸지 않는다.

## 명시적 한계

동봉 planner는 정렬된 정적 시계열을 메모리에 읽는 소규모 참조 구현이다. 데이터 발표 지연, 실제 입수 시각, 과거 수정 이력은 검증하지 않는다. 다른 달력이나 ragged panel은 외부 adapter가 필요하다.

동봉 실행기는 외생변수 학습, full HPO, 분산/GPU 스케줄링, 서명된 immutable registry와 물리적 holdout 접근 제어를 제공하지 않는다. adapter의 실제 학습 자료나 예산 집행은 별도 감사 대상이다. runtime 설정 문자열만으로 공정성이 증명되지 않는다.
