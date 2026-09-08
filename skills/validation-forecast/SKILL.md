---
name: validation-forecast
description: "Audit and score time-series forecasts AFTER model execution against the frozen plan. Verify whether TSCV ran with the planned folds, periods, window and refit rules; inspect leakage evidence, forecast coverage, baselines, metrics and uncertainty; produce a traceable leaderboard. Use for 예측 후 검증, TSCV 실행 여부 확인, 예측 결과 감사, 모델 비교, 리더보드. Do not choose new splits, windows or metrics from results, replan, or train models. Pre-execution design belongs to plan-forecast."
---

# 예측 후 검증

이미 생성된 예측 결과가 **계획대로 실행됐고 비교 가능한지** 확인한다. “TSCV를 했는가?”, “정한 기간과 Fold를 모두 실행했는가?”는 이 스킬의 책임이다. 기간·Fold 수·expanding/sliding 선택은 [plan-forecast](../plan-forecast/SKILL.md)에서 먼저 정한다.

## 범위와 실행 원칙

현재 요청과 파일에서 예측 원장, 사전 protocol, 실행 로그를 찾는다. 확인 가능한 정보는 다시 묻지 않는다. 점수표만 읽고 검증을 끝내지 않으며, 가능한 감사·채점·보고서를 실제로 작성한다. 실행하지 않은 모델이나 검사에 결과를 만들지 않는다.

이 단계에서 split, Fold 수, window, horizon, 주 지표, 후보나 seed를 결과에 맞춰 바꾸지 않는다. 모델을 새로 학습하거나 HPO를 실행하지 않는다. 변경이 필요하면 원래 결과를 보존하고 plan-forecast에서 새 protocol/version을 만든 뒤 별도 실행으로 넘긴다.

시간순 학습 경계, 전처리와 test 누수 검사는 유지한다.

## 1. 계획과 결과 확보

동결된 protocol, lock, origin 목록, 가능한 경우 fold_plan.csv와 계획서, 후보별 run.json·forecasts.jsonl, Fold/fit 로그, 코드·전처리·튜닝·calibration 기록을 읽는다. 데이터·설정 hash와 모델 명세가 같은지 확인한다. `expected.jsonl` 정답은 평가 프로세스에서만 읽는다.

사전 계획이 없으면 **사후 탐색 감사(RETROSPECTIVE)**로 표시한다. 결과로 계획을 역작성해 사전 동결됐다고 주장하지 않는다. 검토 가능한 누수·표본·성능은 기술적으로 보고하되 계획 준수는 `UNKNOWN`이다. 동봉 scorer에 필요한 lock을 만들려고 이 단계에서 새 계획을 몰래 생성하지 않는다.

정답이 아직 실현되지 않았다면 출력 형식·누락·경계만 확인하고 성능 지표는 평가 대기로 남긴다. 사용자가 계획만 요청했거나 예측이 없으면 plan-forecast로 넘긴다.

## 2. 계획 준수와 누수 감사

[단계별 계약](references/stage-contract.md)의 사후 항목과 [누수 기준](references/leakage.md)을 사용한다. [준수표 틀](assets/compliance-template.csv)에 계획값, 실제값, 증빙 경로와 `PASS`·`FAIL`·`UNKNOWN`을 기록한다.

| 검토 항목 | 확인할 실제 증빙 |
|---|---|
| TSCV 실행 | 실제 origin/Fold 로그, 시계열별 Fold 수, train/target 기간과 관측 수 |
| 학습 창·재학습 | expanding/sliding 적용, 창 길이, 실제 refit 시점과 fit 로그 |
| 분할·튜닝 | stride·horizon·gap·purge·내부 split, HPO trial·early stopping·holdout 사용 기록 |
| 학습·전처리 누수 | scaler·imputer·feature/lag 선택·분해의 실제 fit 구간 |
| Label·외생변수 | multi-horizon label 경계, 미래 가격·수급 실제값 유입 |
| Calibration | horizon별 OOS 잔차 pool, 잔차 실현 시점, 서로 다른 horizon 잔차 혼합 여부 |
| 선택 | ensemble 가중치·임계값 선택에 final test를 썼는지 |
| 사전학습 | checkpoint·중복 정책과 증빙, unknown을 clean zero-shot으로 바꿨는지 |
| 표본·실패·예산 | 모든 series×origin×horizon×seed, 실패/미제출, 재학습·계산 예산 로그 |

Calibration residual pool은 **horizon별로 분리**한다. H1 오차는 H1 보정에만, H4 오차는 H4 보정에만 사용한다. 서로 다른 horizon의 오차를 하나의 pool에 섞으면 계획 선택의 문제가 아니라 고정 규칙 위반으로 `FAIL` 처리한다.

예측 행이 모두 있다는 사실만으로 **TSCV를 실제로 실행했다거나 매 Fold 재학습했다고 판정하지 않는다.** 학습 로그가 없으면 해당 항목은 `UNKNOWN`이다. `metrics.fold_origins`로 만든 성능 보고 블록도 실제 TSCV 실행 증거가 아니다.

cutoff 필드는 선언값이다. 코드 경로와 로그를 확인해야 전처리 감사를 `reviewed`로 기록할 수 있다. 필요한 경우 미래 관측값만 바꾸는 회귀 실험으로 과거 입력과 예측의 불변성을 검사한다. 이런 진단 재실행은 사용자 요청 범위 안에서만 수행하고 원래 평가 결과와 구분한다.

## 3. 고정된 조건으로 채점

동일한 `series_id × origin × horizon × seed`를 평가한다. 실패 Fold 삭제, test의 마지막 batch 제외, 유리한 horizon·seed만 남기는 행위는 허용하지 않는다. 성공한 일부 표본의 점수는 진단용으로만 표시하고 공정한 순위에 합치지 않는다.

[지표 정의](references/metrics-inference.md)에 따라 원래 단위의 MAE·MSE·RMSE·bias, 학습 자료로 계산한 MASE/RMSSE, **동일 OOS naive** 대비 개선율을 확인한다. MASE<1만으로 같은 test의 naive보다 낫다고 결론내리지 않는다. 분모가 0이면 미정의로 남긴다.

제출된 baseline과 후보를 함께 채점한다. 기준선이 없으면 이를 누락으로 보고하며 validation 모드가 임의로 모델 실행을 시작하지 않는다. 기존 scorer는 원장에 고정된 naive 값으로 비교할 수 있지만 미제출 baseline의 실행 완료를 주장하지 않는다.

전체 평균과 함께 horizon·사전 국면·보고 블록·seed별 성능, 최악 구간과 표본 수를 본다. 서로 다른 단위의 raw RMSE를 바로 평균하지 않는다. 같은 정보·예산·학습·출력 조건의 track 안에서만 순위를 비교한다.

## 4. 불확실성과 통계검정

quantile grid·교차 여부를 확인하고 pinball, coverage, width, interval score, 조건을 충족한 WIS를 해석한다. 넓기만 한 예측구간을 개선으로 보고하지 않는다. WIS·mean pinball을 정확한 CRPS라고 부르지 않는다.

통계검정은 protocol에서 활성화하고 가정을 검토한 경우에만 실행한다. DM-HAC는 비중첩 비교의 대표본 진단이며 nested 비교나 작은 표본에 일괄 적용하지 않는다. 겹친 horizon과 seed를 독립 표본으로 늘리지 않는다. 평균 손실 차이 CI와 예측구간을 구별하고 사전 family에 Holm 보정을 적용한다. 비유의 결과는 동등성 증명이 아니다.

CRPS, conformal 학습, MCS/SPA, Clark-West, Giacomini–White는 동봉 구현이 아니다. Conformal을 외부에서 썼다면 보정 잔차의 시간 경계와 distribution shift를 감사하고, residual pool이 horizon별로 분리됐는지 확인한다. 지원되지 않은 기능을 실행했다고 보고하지 않는다.

## 5. 판정과 보고

[보고서 틀](assets/report-template.md)에 현재 판정과 근거를 먼저 작성한다. 계획 준수표, 자동 scorer의 audit, 코드 감사와 성능 해석을 구분한다. **`ELIGIBLE`은 실행 증빙 감사의 PASS나 배포 승인을 대신하지 않는다.** 중요한 계획 위반은 전체 판정에 반영하고 증빙이 없으면 추가 검증 필요로 남긴다.

개발 결과는 후보 선택 자료다. Final 결과는 사전 승인한 모델 명세과 학습 정책을 사용했는지 확인하며, 결과를 보고 가중치·임계값·후보를 다시 고른 사실을 숨기지 않는다. 예측력을 구매 성과·수익·인과효과로 바꾸어 표현하지 않는다.

## 실행

`$SKILL_DIR`는 이 validation-forecast 디렉터리다. Python 3.11 이상과 [기존 의존성](scripts/requirements.txt)을 사용한다. 아래 명령은 기존 계획과 예측만 읽고 새로운 결과 폴더에 채점한다.

```bash
python "$SKILL_DIR/scripts/validation_forecast.py" \
  --plan ./experiment-v1/plan \
  --runs ./runs/naive/run.json ./runs/model-a/run.json \
  --out ./evaluation-v1
```

명령은 자동 원장 검사와 지표 계산을 담당한다. 실제 학습 코드·로그와 계획 준수표의 수동 감사까지 자동 실행하지 않는다. [실행 문서](references/runtime.md)에 파일별 역할을 구분한다.

## 공통 자료와 변경 점검

[Protocol 계약](references/protocol.md), [Adapter 계약](references/adapters.md), [논문 근거](references/sources.md), [Agent 운영](references/astra-prompting.md), [행동 평가 사례](assets/behavior-evals.json)를 필요할 때 읽는다. 공통 evaluator·schema는 이 폴더에 한 벌만 두며 plan-forecast가 참조한다. 두 스킬을 같은 checkout에서 함께 설치한다.

변경 후 기존 수치 회귀 테스트와 두 단계의 실행 테스트를 돌린다. Python 테스트 통과와 실제 호스트에서의 스킬 호출 성공을 구분한다.
