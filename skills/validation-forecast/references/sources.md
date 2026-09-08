# 근거와 구현 범위

## 첨부 자료

**[P1]** Hewamalage, H., Ackermann, K., Bergmeir, C. *Forecast evaluation for data scientists: common pitfalls and best practices*. Data Mining and Knowledge Discovery 37, 788–832 (2023). DOI: [10.1007/s10618-022-00894-5](https://doi.org/10.1007/s10618-022-00894-5). 사용본: `s10618-022-00894-5(1).pdf`, 45쪽. 온라인 공개 2022년 12월, 저널 연도 2023년을 구분한다.

**[P2]** Qiu, X. et al. *TFB: Towards Comprehensive and Fair Benchmarking of Time Series Forecasting Methods*. PVLDB 17(9), 2024. DOI: [10.14778/3665844.3665863](https://doi.org/10.14778/3665844.3665863). 사용본: `2403.20150v4.pdf`, arXiv v4, 2025-08-18, 14쪽. 원래 학회 출판 연도와 첨부 버전을 구분한다. [논문 페이지](https://arxiv.org/abs/2403.20150v4).

**[U0]** 사용자가 앞서 첨부한 `time_series_validation_seed_safe_v2_ko(1).pdf`, 25쪽, 및 검증·리더보드를 먼저 구축한다는 대화의 요구사항. 사용자 설계안이며 동료심사를 거친 단일 검증 표준으로 취급하지 않는다.

원문 PDF·그림을 이 스킬에 재배포하지 않는다. 아래는 개념을 실행 절차로 옮긴 설계이며 TFB 실험 결과를 재현했다는 주장이 아니다.

## 규칙별 근거

| 규칙 | 직접 근거 | 이 패키지의 적용 |
|---|---|---|
| 단순하고 적절한 baseline | P1 §3.1, PDF 7–14쪽 | naive 필수; 계절성에 맞는 seasonal baseline 검토 |
| 그래프 모양보다 수치 평가 | P1 §3.4, PDF 15–17쪽 | forecast plot은 sanity check로만 사용 |
| Fold 내부 전처리 | P1 §3.5, PDF 17–19쪽 | 전처리 cutoff 검사와 코드 감사를 분리 |
| Rolling origin, expanding/sliding | P1 §4.1, PDF 20–24쪽 | task별 기간·stride·재학습 주기를 명세 |
| Randomized CV의 조건부 타당성 | P1 §4.1.3, PDF 22–23쪽 | blanket 금지로 인용하지 않음; 기본 경로는 chronological |
| 재학습 정책 | P1 PDF 21쪽; P2 §4.3.1, PDF 7쪽 | 매 origin refit을 모든 모델에 일괄 강제하지 않음 |
| 지표의 정의역·예측 함수 | P1 §4.2, PDF 25–36쪽 | mean/median, 0 분모, 서로 다른 scale을 구분 |
| MASE의 training scale | P1 §4.2; P2 Eq. 14, PDF 7쪽 | test naive 상대오차를 별도로 계산 |
| 통일된 네 계층과 interface | P2 §4.4/Fig. 7, PDF 8쪽 | 데이터·모델·평가·보고를 분리 |
| Test drop_last의 영향 | P2 §1, PDF 3쪽; §5.1.2, PDF 9쪽 | 예상 평가 키와 제출 키를 대조 |
| 데이터·모델 계열의 다양성 | P2 §4.1–4.2 | 지원/실패/미지원 후보를 함께 기록 |
| 다중 비교 | P1 §4.3, PDF 34–39쪽 | 정의한 family에 Holm 적용; seed/origin 독립성 오해 방지 |

## 사용자 설계에서 확장한 부분

FM 중복 상태, 프로토콜 hash, model registry, final approval, 위기 국면, worst Fold, 계산 예산 track과 실패 후보 유지 정책은 [U0]와 이 패키지의 운영 설계다. P1은 주로 **점예측 평가**를 다루며 P2의 지표도 점예측 중심이다. 두 논문이 이 모든 기능을 완성형으로 제안했다고 쓰지 않는다.

P2의 7:1:2/6:2:2 split, horizon 목록, 최대 8개 하이퍼파라미터 집합은 논문의 실험 설정이다. 보편적 권장값으로 복사하지 않았다. 동일 trial 수가 동일 계산량이라는 가정도 하지 않는다.

[U0]의 “MASE<1이면 naive보다 우수”는 training scale과 OOS baseline을 구별해 구현했다. 이전 대화에서 모델 계열별 track을 나누는 예시는 반드시 따라야 하는 규칙으로 보지 않는다. 동일 정보·예산·학습 조건이면 계열 간 비교가 가능하고, 조건 차이를 track으로 표현한다.

## 추가 확인한 원문

**[E1]** Bracher, J., Ray, E. L., Gneiting, T., Reich, N. G. *Evaluating epidemic forecasts in an interval format*. PLOS Computational Biology 17(2), e1008618 (2021). [원문](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1008618). §2의 quantile/interval scoring을 확률 지표 확장의 근거로 사용한다. WIS와 CRPS를 구분하며 역학 도메인의 성능 결과를 원자재에 일반화하지 않는다.

**[E2]** Diebold, F. X., Mariano, R. S. *Comparing Predictive Accuracy*. Journal of Business & Economic Statistics 13(3), 253–263 (1995). [원문 소개와 초록](https://doi.org/10.1080/07350015.1995.10524599). 원저자 초록은 forecast errors가 non-Gaussian일 수 있다고 설명한다. P1 §4.3의 정규성 설명을 원자료의 Gaussian 필수 조건으로 단순화하지 않았다. 동봉 코드는 Bartlett HAC를 사용하는 대표본 DM-style 구현이며 원저자의 모든 검정이나 소표본 보정을 재현하지 않는다.

## 스킬 형식

**[O1]** [OpenAI skill-creator](https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md): 짧은 SKILL.md와 이름·description, 실행 스크립트, 필요할 때 읽는 references/assets를 분리하는 구조를 참고했다. [agents/openai.yaml 설명](https://github.com/openai/skills/blob/main/skills/.system/skill-creator/references/openai_yaml.md)도 확인했다.

**[O2]** [Build skills](https://learn.chatgpt.com/docs/build-skills), [Package your plugin](https://developers.openai.com/plugins/build/plugins). 확인일 2026-09-07. 당시 openai/skills README는 deprecated 안내와 현재 plugin 문서 링크를 제공했다. 이 패키지는 standalone local skill을 기본으로 하며 별도 배포물에는 skill-only plugin manifest만 덧붙인다. 제품 내 설치와 실제 agent 호출 검증은 파일 구조·수치 테스트와 구분한다.

## GPT-6 Astra 운영 근거

**[O3]** OpenAI, [Model guidance — Using GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model), 확인일 2026-09-07. 이 스킬의 자율 실행, 결과를 바꾸는 경우에만 집중 질문, 명시적 지시 우선순위, 간결한 작성 방식, 필요할 때 병렬 위임, 변경 위험에 맞춘 테스트 지침에 반영했다.

**[O4]** OpenAI, [GPT-6 Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra), 확인일 2026-09-07. API integration의 `gpt-6-astra` 모델 ID, Responses API tool 지원, `low`/`medium`/`high`/`xhigh`/`max` reasoning effort와 모델 제약을 확인하는 기준으로 사용한다. 이 모델 설정은 forecast evaluation의 통계적 타당성을 대신하지 않는다.
