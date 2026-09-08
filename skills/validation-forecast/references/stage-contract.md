# 예측 전·후 역할과 인계 계약

하나의 검토 주제를 시점에 따라 나눈다. 예측 전에는 값을 결정하고, 예측 후에는 실제 실행값과 증빙을 대조한다. 스킬 이름만 바꾸고 두 단계가 같은 질문을 반복하지 않는다.

| 주제 | plan-forecast — 실행 전 결정 | validation-forecast — 결과 생성 후 확인 |
|---|---|---|
| 목표 | target·단위·horizon·예측 시점 정의 | 예측값·정답·역변환이 같은 목표를 가리키는지 |
| TSCV | 방식, 평가 기간, 시계열별 Fold 수와 분할 일정 | 실제 TSCV 실행 여부, Fold 수·기간·관측 수 일치 |
| Window | expanding/sliding 선택, 최소·최대 학습 길이 | 각 origin의 실제 학습 범위와 창 이동 일치 |
| Stride·horizon | 예측 간격과 horizon 목록, 최대 target 경계 | 요청한 모든 origin/horizon의 정렬과 누락 |
| 재학습 | fit 주기, state update와 재사용 규칙 | fit 로그·모델 상태·입력 갱신 기록 |
| 내부 튜닝 | 내부 시간순 split·gap/purge·trial 예산 | trial·label·early stopping 구간의 실제 경계 |
| 전처리 | scaler·imputer·변수/lag 선택·분해의 fit 정책 | 실제 fit 데이터, 코드 경로와 상태 hash |
| 입력·사전학습 | 외생변수 정책, checkpoint·중복 정책 | 미래 실측값 유입, 학습 데이터 중복 증빙 |
| 기준선 | Naive 필수 등록, drift/계절 기준선·period 선택 | 같은 OOS 표본의 기준선 성능과 제출 상태 |
| 지표 | 주 지표·mean/median·집계 가중치·방향 정의 | 정의대로 계산했는지, 개선 폭·편향·미정의 분모 |
| 확률예측 | quantile grid, 보정 구간·방법 | crossing, pinball·coverage·width·interval score·WIS |
| 통계검정 | 활성화 여부, 비교 가정, HAC lag, family | 표본·의존성·가정 충족, 검정 보류, CI·Holm 해석 |
| 안정성 | horizon·seed·국면·보고 블록 정의 | 해당 구간의 성능·최악 구간·표본 수 |
| 비용·실패 | 후보·seed·계산 예산·누락 처리 정책 | 실제 비용·실패·미제출·표본 coverage |
| 최종 평가 | 미사용 구간, 모델 명세·가중치·승인 동결 | test 재선택 여부, 승인 명세와 실제 실행 일치 |

## Fold의 의미

동봉 실행기의 rolling Fold는 `series_id × origin` 하나다. 같은 Fold에서 여러 horizon과 seed를 평가한다. 서로 다른 시계열의 Fold 수를 더해 한 시계열의 TSCV 횟수라고 쓰지 않는다. 매 Fold refit할지는 `tracks.*.refit_policy`가 결정하며, 기본 baseline만 `each_origin`을 지원한다.

`metrics.fold_origins`는 성능 보고를 위해 연속 origin을 몇 개씩 묶는지 정한다. `fold_metrics.csv`의 Fold는 이 **보고 블록**이다. 이는 실제 TSCV 분할 수나 재학습 횟수가 아니다. 계획 출력은 `rolling_folds_per_series`와 `report_blocks_per_series`를 따로 기록한다.

K개의 임의 train/test 구간, nested TSCV의 내부 Fold, gap/purge와 주기적 refit은 별도 adapter 명세가 필요하다. 해당 설정을 기본 실행기에 없는 schema 필드로 넣지 않는다. 기본 계획기의 `n_train`은 허용된 원시 학습 창의 관측 수다. lag/label 생성 후 실제 훈련 표본 수나 주기적 refit 모델의 마지막 fit 크기와는 다를 수 있다.

## 실행 전 산출물

`plan.md`에는 선택값·근거·미결정 사항과 추가 adapter 명세를 남긴다. 데이터가 없으면 DRAFT다. 계획기는 원본 protocol을 검사한 뒤 다음 묶음을 새 폴더에 만든다.

| 파일 | 역할 |
|---|---|
| `protocol.json` | 검사한 설정 사본 |
| `fold_plan.csv` | 시계열별 rolling Fold 일정, train/target 경계·관측 수, 보고 블록 |
| `planning_summary.json` | 실제 계획 Fold 수, 보고 블록 수, 예상 평가 행 수·hash |
| `plan/lock.json` | protocol·데이터·평가 키의 기존 동결 계약 |
| `plan/origins.jsonl` | 모델 실행자에게 전달할 일정 |
| `plan/omitted_origins.jsonl` | 계획 단계의 공통 warm-up·horizon 경계 제외 기록 |
| `plan/expected.jsonl` | 평가 전용 정답. 모델·튜닝 입력으로 전달 금지 |

`fold_plan.csv`는 lock의 origin 일정에서 파생한 검토용 파일이다. scorer의 기준 원장은 기존 lock/expected다. 검증할 때 계획 CSV의 hash를 planning_summary와 확인하고 protocol·origins와 일치하는지도 대조한다. CSV만 바꿔 평가 계획을 바꾼 것으로 취급하지 않는다.

## 단계 사이의 모델 실행

학습·예측은 모델 adapter나 기존 실행기가 수행한다. 계획만 요청했거나 예측 결과 검증만 요청했을 때 자동으로 실행을 추가하지 않는다. 사용자가 전체 실행을 요청한 경우에는 계획 동결 후 별도 실행 단계를 수행한다. 모델별 run.json·forecasts.jsonl과 Fold/fit·전처리·튜닝 로그를 남긴다.

## 예측 후 판정

계획 준수표의 필수 열은 `item,planned,observed,evidence,status`다. `PASS`는 증빙으로 일치 확인, `FAIL`은 위반 확인, `UNKNOWN`은 판단에 필요한 증빙 부족을 뜻한다. 이 표는 agent/검토자가 작성하며 동봉 scorer가 임의 코드 내부를 자동 검사한 결과가 아니다.

원장 coverage=1이나 scorer의 `ELIGIBLE`만으로 TSCV 실행을 PASS로 처리하지 않는다. 계획·Fold 로그·fit 경계를 함께 확인한다. 중요한 항목이 UNKNOWN이면 전체 보고서에는 추가 검증 필요, 위반이 있으면 계획 미준수로 표시하고 자동 순위와 구분한다.

사전 계획이 없으면 RETROSPECTIVE로 기술한다. 사후 작성한 lock을 사전 등록의 근거로 바꾸지 않는다. 재설계는 새 plan-forecast 작업과 새 protocol/version으로 진행하고 기존 결과를 보존한다.
