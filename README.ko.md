# Forecast Skills

예측 전 계획과 예측 후 검증을 두 스킬로 나눕니다.

[English](README.md) · [예측 전 계획](skills/plan-forecast/SKILL.md) · [예측 후 검증](skills/validation-forecast/SKILL.md) · [단계별 계약](skills/validation-forecast/references/stage-contract.md)

| 주제 | plan-forecast — 예측 전 | validation-forecast — 예측 후 |
|---|---|---|
| TSCV | 몇 번, 어느 기간, 몇 개 Fold로 실행할지 결정 | 실제 TSCV를 했는지, 정한 Fold·기간을 지켰는지 확인 |
| Window | expanding/sliding과 학습 길이 선택 | 실제 학습 창과 이동 방식 대조 |
| 학습·전처리 | refit·튜닝·feature 선택 규칙 설정 | Fold/fit·전처리·튜닝 로그 감사 |
| 기준선·지표 | naive·계절 주기·주 지표·집계 방식 고정 | 같은 OOS 표본으로 비교·채점 |
| 불확실성 | quantile grid·calibration·검정 계획 | 구간 성능·DM-HAC·Holm 등 확인 |
| 결과물 | 계획서, protocol, Fold 일정, lock | 계획 준수표, 감사 보고서, 지표·리더보드 |

학습·예측은 두 단계 사이에서 모델 adapter가 수행합니다. 계획만 요청하면 학습·채점하지 않고, 결과 검증 중에는 점수에 맞춰 split·window·지표를 바꾸지 않습니다. 실행까지 요청하면 계획 동결 → 모델 실행 → 결과 검증 순서로 진행합니다.

**TSCV Fold 수와 보고 블록 수는 다릅니다.** 동봉 실행기의 rolling Fold는 시계열별 origin 하나입니다. `metrics.fold_origins`는 성능을 묶어 보는 보고 블록 크기이며 실제 재학습 횟수도 아닙니다.

## 설치와 호출

두 스킬을 같은 저장소에서 함께 설치합니다. 공통 evaluator·schema·참조 문서는 `skills/validation-forecast/`에 한 벌만 있으며 계획 스킬이 이를 참조합니다. plan-forecast 폴더만 복사하는 독립 설치는 지원하지 않습니다.

저장소 루트에서 실행합니다. 기존 설치를 덮어쓰지 않습니다.

```bash
for name in plan-forecast validation-forecast; do
  test -f "$PWD/skills/$name/SKILL.md" || exit 1
  dest="$HOME/.agents/skills/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    printf 'Existing installation: %s\n' "$dest"
    exit 1
  fi
done
mkdir -p "$HOME/.agents/skills"
for name in plan-forecast validation-forecast; do
  ln -s "$PWD/skills/$name" "$HOME/.agents/skills/$name"
done
```

호출 예시:

```text
$plan-forecast
TSCV 기간과 시계열별 Fold 수, expanding/sliding window를 정하고
protocol과 Fold 일정을 고정해줘. 아직 모델은 실행하지 마.
```

```text
$validation-forecast
기존 계획과 예측 원장, 실제 Fold/fit 로그를 대조해줘.
TSCV 실행 여부와 계획 준수를 확인하고 결과를 채점해줘.
```

기존 `$validate-time-series` 통합 호출은 두 이름으로 전환합니다. 이전 설치나 링크를 자동 삭제하지 않으며 새 스킬을 사용할 때는 새 이름으로 호출합니다. Plugin 식별자는 저장소 이름을 유지하고 `skills/`의 두 스킬을 등록합니다. 실제 호스트에서의 설치·호출 성공은 코드 테스트와 별도입니다.

## 실행

Python 3.11 이상을 사용합니다. Target CSV는 `series_id,timestamp,value` 세 컬럼입니다. 데이터 이용 가능 시점과 Vintage 검증은 두 스킬 모두에서 제외합니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/validation-forecast/scripts/requirements.txt

# 1. 예측 전: 설정 검사, 계획 동결, Fold 일정 생성
.venv/bin/python skills/plan-forecast/scripts/plan_forecast.py \
  --protocol ./protocol.json --data ./target.csv --out ./experiment-v1

# 2. 별도 실행 단계: 등록된 기준선 또는 모델 adapter로 예측 생성
.venv/bin/python skills/validation-forecast/scripts/tsvalidate.py baseline \
  --plan ./experiment-v1/plan --data ./target.csv --method naive --out ./runs/naive

# 3. 예측 후: 기존 계획과 제출 예측 채점
.venv/bin/python skills/validation-forecast/scripts/validation_forecast.py \
  --plan ./experiment-v1/plan --runs ./runs/naive/run.json --out ./evaluation-v1
```

위 명령은 데이터와 protocol을 준비한 뒤 사용합니다. 다른 등록 후보가 미제출이면 MISSING_RUN으로 남습니다. 계획기에 `--expected-folds K`를 추가하면 시계열별 실제 계획 수가 K와 맞는지 검사합니다. 학습·전처리·label 경계, 동일 평가 키, 기준선 비교와 final holdout 검사는 유지합니다.

계획기는 `fold_plan.csv`, `planning_summary.json`, `protocol.json`, `plan/`을 만듭니다. `plan/expected.jsonl`은 평가 전용 정답이며 모델 입력에 전달하지 않습니다. 기본 lock은 정답이 있는 오프라인 벤치마크용입니다. 보호된 holdout은 평가 담당자가 다루고 정답이 없는 미래 예측은 계획 초안으로 남깁니다.

검증 명령은 원장·hash·cutoff·표본과 지표를 검사합니다. 실제 TSCV·refit·전처리 수행 여부는 코드·로그로 따로 확인해야 합니다. [계획 준수표](skills/validation-forecast/assets/compliance-template.csv)는 검토자가 작성하며, `ELIGIBLE`만으로 TSCV 실행·누수 없음·배포 승인을 주장하지 않습니다. 사전 계획이 없으면 사후 탐색 감사로 표시합니다.

## 테스트와 지원 범위

```bash
.venv/bin/python skills/validation-forecast/scripts/test_validation.py
.venv/bin/python tools/test_forecast_modes.py
.venv/bin/python tools/test_repository.py
.venv/bin/python skills/validation-forecast/scripts/demo.py --out ./demo-output
```

데모는 합성 자료만 사용하며 모델 다운로드·유료 API·GPU가 필요하지 않습니다. 출력 폴더는 덮어쓰지 않습니다. CI는 Python 3.11/3.12/3.13에서 검사하고 추적된 소스만 묶은 `forecast-skills-source` artifact를 남깁니다.

기존 Naive·Drift·Seasonal Naive, 점예측·제출 분위수 지표, 선택적 DM-HAC·Holm, 실패 보존과 track별 리더보드를 재사용합니다. 개별 ARIMA·XGBoost·딥러닝·Foundation Model 학습 adapter, full HPO, 임의 K-fold/nested split·gap/purge 실행, CRPS·conformal 학습·MCS·SPA·Clark-West·Giacomini–White는 기본 구현이 아닙니다. [실행 계약](skills/validation-forecast/references/runtime.md)에서 문서 지침과 구현을 구분합니다.

## 라이선스

[MIT License](LICENSE)를 따릅니다.

## 참고 문헌

| 저자 | 연도 | 논문 | 학술지 |
|---|---|---|---|
| Hewamalage, H., Ackermann, K., Bergmeir, C. | 2023 | [Forecast evaluation for data scientists: common pitfalls and best practices](https://doi.org/10.1007/s10618-022-00894-5) | Data Mining and Knowledge Discovery, 37, 788–832 |
| Qiu, X. et al. | 2024 | [TFB: Towards Comprehensive and Fair Benchmarking of Time Series Forecasting Methods](https://doi.org/10.14778/3665844.3665863) | PVLDB, 17(9) |
| Bracher, J., Ray, E. L., Gneiting, T., Reich, N. G. | 2021 | [Evaluating epidemic forecasts in an interval format](https://doi.org/10.1371/journal.pcbi.1008618) | PLOS Computational Biology, 17(2), e1008618 |
| Diebold, F. X., Mariano, R. S. | 1995 | [Comparing Predictive Accuracy](https://doi.org/10.1080/07350015.1995.10524599) | Journal of Business & Economic Statistics, 13(3), 253–263 |

논문별 반영 범위와 구현상의 구분은 [근거와 구현 범위](skills/validation-forecast/references/sources.md)에 정리했습니다. TFB는 2024년 출판 논문이며, 참고한 원문은 [arXiv v4 (2025)](https://arxiv.org/abs/2403.20150v4)입니다.
