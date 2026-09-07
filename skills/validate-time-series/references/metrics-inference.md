# 지표와 통계검정

## 점예측

오차의 부호는 `e = actual − forecast`이다. 양의 bias ME는 과소예측을 뜻한다. MAE는 절대오차 평균, MSE는 제곱오차 평균, RMSE는 MSE의 제곱근이다. 먼저 실제 목표 단위로 계산한다. [P1 §4.2]

MAE/MASE는 중앙값, MSE/RMSE는 평균 예측과 연결된다. 모든 모델을 같은 평가 목표에 맞춰 튜닝할 기회를 주고 학습 손실이 다르면 기록한다. 보조 지표를 여럿 보고할 수 있지만 test를 보고 가장 유리한 지표를 주 지표로 바꾸지 않는다. [P1 pp. 813–814]

0이나 음수에 가까운 자료에 MAPE를 기본 적용하지 않는다. 비율·로그 기반 지표의 정의역을 확인한다. 이 구현은 MAPE와 R²를 기본 점수에서 제외한다. 시각적으로 잘 따라가는 선만으로 예측력을 주장하지 않는다. [P1 §3.3–3.4]

## MASE와 naive 대비 성능

학습값 `y[1:T]`, 계절 주기 `m`에서 다음 scale을 쓴다.

```
scale_abs = mean(abs(y[t] - y[t-m]))  # training only, t=m+1,...,T
scale_sq  = mean((y[t] - y[t-m])**2)
MASE      = mean(abs(test_error) / scale_abs)
RMSSE     = sqrt(mean(test_error**2 / scale_sq))
```

rolling 평가에서는 origin마다 이용 가능한 학습값으로 scale을 구한다. scale이 0이거나 학습 길이가 부족하면 지표는 `null`이고 미정의 건수를 함께 낸다. 분모의 구조변화 민감성도 확인한다. [P1 §4.2; P2 Eq. 14]

MASE의 scale은 **학습 구간의 seasonal/one-step naive 오차**다. 동일 test·horizon에서 계산한 naive의 오차와 같지 않다. 따라서 MASE<1이 동일 OOS naive보다 우수하다는 충분조건은 아니다. 이전 검증 초안의 축약 표현은 이 구현에서 구분했다.

실제 baseline 비교는 같은 origin/horizon/seed의 오차로 계산한다.

```
cell_skill = 1 - metric(model, cell) / metric(naive, cell)
cell = one series × one horizon, all locked origins and seeds
leaderboard_skill = mean(cell_skill)  # equal cell weights
```

0은 naive와 같은 손실, 양수는 개선이다. baseline 손실이 0인 cell이 있으면 자동 macro 순위를 부여하지 않고 `UNDEFINED_BASELINE_SCALE`로 남긴다. 조용히 해당 cell을 빼거나 0/0을 승리로 처리하지 않는다. 이 정책과 동일 가중은 운영 선택이며 보편적인 최적 집계법이라는 주장은 아니다.

동봉 scorer는 seed별 예측을 평균해 앙상블을 만들지 않는다. 각 seed에서 발생한 손실을 동일하게 반영한다. 앙상블을 평가하려면 별도 candidate로 예측 원장을 제출한다.

## 방향·Fold·국면

방향은 origin의 당시 마지막 관측 대비 상승/보합/하락을 비교한다. `direction_tolerance` 이내는 보합이다. 목표가 수익률이나 누적 변화량이면 해당 목표에 맞는 방향 정의를 별도 구현한다.

Fold는 정해진 개수의 연속 origin 블록이다. `fold_metrics.csv`는 series×horizon×block별 점수다. `worst_cell_fold_skill`은 그중 가장 나쁜 값을 뜻한다. `cell_fold_skill_std`는 이 cell들을 섞은 산포이며 순수한 시간 변동성이나 신뢰구간이 아니다. 시계열·horizon을 고정한 Fold 추이를 함께 읽는다.

국면은 미리 정한 origin 날짜 구간으로 자른다. 중첩 구간도 허용하므로 국면 행을 다시 더해 전체 표본 수로 사용하지 않는다. 사후에 정의한 위기 라벨은 진단용이며 실시간 모델 선택 변수로 이용할 수 있다는 증거가 아니다. 정의한 국면에 origin이 없으면 결과 행이 없으므로 보고서에 표본 0이라고 표시한다. [U0 확장]

## 예측구간

동봉 구현은 pinball loss, central interval의 coverage·width·interval score, 대칭 quantile 쌍과 median이 모두 있을 때 WIS를 계산한다. 분위수 교차는 오류로 처리하며 값을 정렬해 조용히 고치지 않는다. `mean_pinball`은 명시한 grid의 단순 평균이고 CRPS가 아니다. [E1]

```
pinball_q(y, f) = max(q*(y-f), (q-1)*(y-f))
IS_alpha = (upper-lower) + (2/alpha)*max(lower-y,0)
                           + (2/alpha)*max(y-upper,0)
WIS = [0.5*abs(y-median) + sum((alpha/2)*IS_alpha)] / (K+0.5)
```

WIS의 각 구간은 q=alpha/2, 1-alpha/2의 central interval이다. 비대칭 grid에서는 지원되는 pinball과 central pair만 계산하고 WIS는 생성하지 않는다. 현재 자동 순위는 point metric 기준이며 확률 지표는 별도 진단 열이다. 확률 순위가 필요하면 probabilistic baseline과 집계 규칙을 추가해 새 protocol로 만든다.

CRPS, sample 분포 평가, conformal 구간 학습은 동봉하지 않는다. sparse quantile로 계산한 근사값을 정확한 CRPS라고 이름 붙이지 않는다. Conformal을 연결할 때는 보정 표본의 시간 의존성, 아직 실현되지 않은 horizon residual과 distribution shift를 점검한다. [E1; U0 확장]

## DM-HAC와 confidence interval

통계검정은 기본 설정에서 꺼져 있다. `enabled=true`와 `assumptions_reviewed=true`를 명시하고 비교가 `non_nested`라고 검토한 경우에만 동봉 DM-HAC를 실행한다. nested/미검토 비교는 p-value를 만들지 않는다.

같은 series×horizon에서 origin별 `d = model loss − naive loss`를 만들고 같은 origin의 seed별 손실 차이를 평균한다. MAE가 주 지표면 절대오차, MSE/RMSE면 제곱오차를 사용한다. RMSE 자체를 한 관측의 loss로 취급하지 않는다.

대표본 정규근사와 Bartlett HAC 장기분산을 사용한다. `hac_lags`는 origin 간격 단위다. 최소 overlap guard는 `ceil(max_horizon/stride)-1`이지만 실제 의존성에는 더 긴 bandwidth가 필요할 수 있다. `min_origins=40`은 기본 예시의 보수적 실행 문턱이지 수학적 충분조건이 아니다. 손실 차이의 안정성·의존성, 재학습이 유도한 의존성, 유한 모멘트와 대표본 근사의 적절성을 검토한다. [E2; 구현 정책]

CI는 같은 HAC 표준오차로 계산한 **평균 손실 차이의 근사 구간**이다. 미래 실제값의 prediction interval과 다르다. 작은 표본, 긴 의존성, 분산 퇴화에서는 검정을 보류한다. 동일한 손실이면 p=1을 반환한다. 이는 모든 데이터에서 두 모델이 동등하다는 뜻은 아니다.

동봉 구현은 HLN small-sample correction이나 bootstrap DM, Clark-West가 아니다. P1 §4.3의 DM 정규성 설명을 원자료가 반드시 Gaussian이어야 한다는 규칙으로 쓰지 않았다. 원저자 논문은 비정규 forecast error도 허용한다고 명시한다. 여기서는 손실 차이의 대표본 정규근사 조건을 따로 검토한다. [P1 §4.3; E2]

## 다중 비교와 선택 편향

사전 등록된 non-naive 후보×series×horizon 전체를 한 family로 두고 Holm 보정을 적용한다. 미실행·미검토·불완전 비교는 p=1인 미검정 가설로 보수적으로 family 크기에 남긴다. 개별 CI에는 동시구간 보정이 없으며 이를 simultaneous CI로 해석하지 않는다.

개발 데이터로 모델을 반복 선택한 편향은 Holm만으로 없어지지 않는다. 유의성·개선 폭·불확실성·운영 비용을 함께 보고 최종 자료에서 재확인한다. [P1 §4.3; 운영 확장]

| 상황 | 추가 검토할 방법 | 동봉 실행 여부 |
|---|---|---|
| 두 forecast의 비중첩 비교 | 손실 의존성을 반영한 DM 계열 | DM-HAC 대표본 진단만 구현 |
| Nested 모델의 MSPE 비교 | Clark-West와 적용 조건 | 미구현 |
| 상태별 조건부 예측력 | Giacomini-White | 미구현 |
| 다수 모델의 우수 집합/benchmark 검정 | MCS / SPA, 적절한 dependent bootstrap | 미구현 |
| 여러 독립적인 dataset의 순위 | Friedman 및 사후 비교 | 미구현 |

같은 시계열의 overlapping Fold를 독립 dataset으로 간주해 Friedman/Nemenyi에 넣지 않는다. MCS에 남았다는 것을 모든 모델의 동등성이나 향후 우위 보장으로 해석하지 않는다. 추가 방법은 검증된 구현과 해당 원문을 확인해 연결한다. [P1 §4.3; U0의 고급검정 확장]
