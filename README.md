# Validate Time Series

검증 기준을 먼저 고정하고, 예측 모델은 같은 평가기에 연결합니다.

[English](README.en.md) · [스킬 지침](skills/validate-time-series/SKILL.md) · [실행 방법](skills/validate-time-series/references/runtime.md) · [논문 근거](skills/validate-time-series/references/sources.md)

`validate-time-series`는 시계열 예측의 데이터 누수, 반복 평가, 기준선 비교와 리더보드 작성을 위한 Agent Skill입니다. 기존 `v1.1.0-astra` 패키지를 배포용 저장소로 정리했습니다. GPT-6 Astra용 작업 지침을 포함하며, 모델 선택은 실행 호스트에서 설정합니다. 스킬을 설치한다고 호스트 모델이 바뀌지는 않습니다.

## 무엇을 검증하나요?

| 검증 영역 | 동봉 실행기 |
|---|---|
| 데이터 이용 가능 시각 | `available_at`을 기준으로 당시 이용 가능한 관측·수정본 조회 |
| 반복 평가 | Expanding / Sliding window, 예측 시점과 Horizon 고정 |
| 기준선 | Naive, Drift, Seasonal Naive |
| 점예측 | MAE, MSE, RMSE, Bias, MASE, RMSSE, 동일 OOS naive 대비 개선율 |
| 확률예측 | 제출된 분위수의 Pinball Loss, Coverage, Width, Interval Score, 조건을 만족하는 WIS |
| 통계검정 | 명시적으로 활성화한 경우 DM-style HAC 진단과 Holm 보정 |
| 리더보드 | 동일 조건의 Track 안에서 순위 산출, Horizon·국면·평가 블록·seed별 진단 |
| 실패 기록 | 누락·실패·미제출 후보 보존, 불완전한 결과는 순위 제외 |

입력값의 시각과 hash를 검사해도 임의 모델 코드의 누수까지 증명되지는 않습니다. 모델 학습과 전처리는 별도 코드 감사가 필요합니다. `ELIGIBLE`은 비교 조건을 충족했다는 뜻이며, 배포 승인이나 미래 성능 보장이 아닙니다.

## 빠른 실행

Python 3.11 이상을 사용합니다. 저장소 루트에서 실행하세요.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/validate-time-series/scripts/requirements.txt
.venv/bin/python skills/validate-time-series/scripts/test_validation.py
.venv/bin/python tools/test_repository.py
.venv/bin/python skills/validate-time-series/scripts/demo.py --out ./demo-output
```

데모는 합성 시계열만 사용합니다. GPU, 모델 다운로드, 유료 API는 필요하지 않습니다. 같은 출력 폴더를 덮어쓰지 않으므로 재실행할 때는 새 `--out` 경로를 지정하세요.

결과는 `demo-output/evaluation/`에 생성됩니다. 실제 실행한 작은 예시는 [합성 데이터 리더보드](docs/example-output/leaderboard.csv)에서 확인할 수 있습니다. 이 예시는 실제 원자재 모델의 성능 근거가 아닙니다.

## Codex 스킬로 설치

로컬 사용자 스킬 경로에 심볼릭 링크를 만듭니다. 기존 설치를 덮어쓰지 않습니다. 아래 명령도 저장소 루트에서 실행하세요.

```bash
DEST="$HOME/.agents/skills/validate-time-series"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  printf '기존 설치가 있습니다. 경로를 확인하세요: %s\n' "$DEST"
else
  mkdir -p "$HOME/.agents/skills"
  ln -s "$PWD/skills/validate-time-series" "$DEST"
fi
```

설치 후 호출 예시입니다.

```text
$validate-time-series

현재 프로젝트의 데이터와 후보 모델을 확인해.
검증 조건을 먼저 고정하고 naive 기준선부터 실행한 다음,
같은 평가 표본으로 후보 모델을 비교하고 리더보드를 만들어줘.
이미 확인할 수 있는 정보는 다시 묻지 말고,
새 비용이나 최종 holdout 승인이 필요한 작업만 구분해줘.
실패한 후보도 기록하고 Horizon별 결과와 누수 감사 근거를 남겨줘.
```

`.codex-plugin/plugin.json`과 `.agents/plugins/marketplace.json`도 포함했습니다. 스킬 폴더는 하나만 유지하고 플러그인에서 같은 폴더를 참조합니다. 실제 Codex 플러그인 설치·호출은 이번 패키징에서 시험하지 않았습니다. 설치 경로와 플러그인 구조의 근거는 [저장소 구성 메모](docs/repository-notes.md)에 있습니다.

## 저장소 구성

```text
validate-time-series/
├── README.md
├── README.en.md
├── LICENSE
├── AGENTS.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .codex-plugin/plugin.json
├── .agents/plugins/marketplace.json
├── .github/workflows/ci.yml
├── skills/validate-time-series/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/
│   ├── references/
│   └── scripts/
├── docs/
│   ├── repository-notes.md
│   ├── publish.md
│   ├── verification.json
│   └── example-output/leaderboard.csv
└── tools/
    ├── publish_github.py
    └── test_repository.py
```

스킬 동작에 필요한 파일은 `skills/validate-time-series/` 안에 있습니다. 저장소 관리 파일을 수정해도 스킬의 평가 로직은 바뀌지 않습니다.

## 모델 추가

[Adapter 계약](skills/validate-time-series/references/adapters.md)을 따라 `run.json`과 `forecasts.jsonl`을 제출합니다. 모델마다 평가 코드를 복제하지 않고 동봉 evaluator로 채점합니다. 실제 명령과 필드 형식은 [실행기 문서](skills/validate-time-series/references/runtime.md)에 있습니다.

ARIMA·XGBoost·딥러닝·Foundation Model의 개별 학습 adapter는 아직 포함하지 않습니다. CRPS, Conformal 학습, MCS, SPA, Clark-West, Giacomini–White도 기본 실행 코드에 없습니다. 지침 제공과 실행 구현을 구분합니다.

## 라이선스

이 프로젝트는 [MIT License](LICENSE)를 따릅니다.

## 참고 문헌

| 저자 | 연도 | 논문 | 학술지 |
|---|---|---|---|
| Hewamalage, H., Ackermann, K., Bergmeir, C. | 2023 | [Forecast evaluation for data scientists: common pitfalls and best practices](https://doi.org/10.1007/s10618-022-00894-5) | Data Mining and Knowledge Discovery, 37, 788–832 |
| Qiu, X. et al. | 2024 | [TFB: Towards Comprehensive and Fair Benchmarking of Time Series Forecasting Methods](https://doi.org/10.14778/3665844.3665863) | PVLDB, 17(9) |
| Bracher, J., Ray, E. L., Gneiting, T., Reich, N. G. | 2021 | [Evaluating epidemic forecasts in an interval format](https://doi.org/10.1371/journal.pcbi.1008618) | PLOS Computational Biology, 17(2), e1008618 |
| Diebold, F. X., Mariano, R. S. | 1995 | [Comparing Predictive Accuracy](https://doi.org/10.1080/07350015.1995.10524599) | Journal of Business & Economic Statistics, 13(3), 253–263 |

논문별 반영 범위와 구현상의 구분은 [근거와 구현 범위](skills/validate-time-series/references/sources.md)에 정리했습니다. TFB는 2024년 출판 논문이며, 참고한 원문은 [arXiv v4 (2025)](https://arxiv.org/abs/2403.20150v4)입니다.
