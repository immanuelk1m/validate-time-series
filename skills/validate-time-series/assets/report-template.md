# 시계열 예측 검증 보고서

## 판단

판정: [후보 비교 가능 / 기준선 개선 근거 부족 / 추가 검증 필요 / 검증 차단]

[어떤 목표·단위·horizon에서 무엇을 검증했는지, 어떤 근거가 부족한지 적는다. ELIGIBLE과 배포 승인을 구분한다.]

## 데이터와 비교 조건

| 항목 | 확인값 |
|---|---|
| Benchmark / protocol version / phase | |
| Dataset SHA-256 / truth_as_of | |
| 목표·단위·horizon 단위·시간대 | |
| Origin 범위·stride·horizon·학습 길이 | |
| 이용 가능 시각과 수정 이력 근거 | |
| Split·전처리·feature 선택·재학습 정책 | |
| Track별 정보 집합·예산·학습 방식 | |
| 후보·seed·주 지표·집계 규칙 | |
| 최종 선택 승인 및 holdout 열람 이력 | |

## 감사 결과

[검사한 실제 코드·데이터 범위·로그·source hash를 적는다. 자동 timestamp 검사와 수동 코드 감사를 나눈다. 미확인 항목, 실패/미제출 후보와 누락 표본 수를 숨기지 않는다.]

## 예측 성능

[같은 track 안에서만 비교한다. series×horizon별 point metric, OOS naive skill, MASE/RMSSE와 미정의 분모 수를 제시한다. 서로 다른 단위의 raw RMSE를 바로 평균하지 않는다.]

## 안정성과 국면

[고정된 series·horizon에서 Fold 변화, 최악 구간, seed 산포를 읽는다. cell_fold_skill_std를 신뢰구간으로 해석하지 않는다. 국면별 표본 수를 적고 데이터에 없는 위기 상황은 미검증이라고 쓴다.]

## 예측 불확실성

[quantile grid, coverage·width·pinball·interval score·WIS 중 실제 계산한 값을 제시한다. 출력이 없으면 미지원으로 적는다. mean-loss confidence interval과 prediction interval을 구분한다.]

## 통계적 차이

[주 loss, 비교 단위, 유효 origin 수, HAC lag, 검토한 가정, 다중 비교 family, p-value/보정값, 평균 손실 차이와 CI를 적는다. nested/소표본/강한 의존성으로 보류한 경우를 명시한다. 유의하지 않음을 동등성으로 표현하지 않는다.]

## 최종 평가와 배포 경계

[개발 점수라면 선택 자료라는 사실을 명시한다. 최종 평가라면 어떤 명세를 언제 동결했고 이후 무엇을 변경했는지 적는다. 예측력만으로 구매 성과·수익·인과 효과를 주장하지 않는다. 실제 운영 기준이 없으면 배포 승인도 하지 않는다.]

## 재현 자료

[protocol, data/model/environment/code hashes, 예측 원장, loss ledger, 실행 명령, 실패 기록과 비용 기준을 연결한다. 주장 옆에 P1/P2/U0/E1/E2 중 실제 근거를 연결하고 미구현 기능을 구현 결과로 제시하지 않는다.]
