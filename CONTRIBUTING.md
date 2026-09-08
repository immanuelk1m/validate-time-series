# 변경 가이드

수정 전에 [예측 전 계획](skills/plan-forecast/SKILL.md)과 [예측 후 검증](skills/validation-forecast/SKILL.md) 중 해당 단계의 지침과 관련 코드를 읽습니다. 평가 로직은 기존 실행기를 수정하고 모델마다 별도 채점기를 만들지 않습니다.

새 모델은 [adapter 계약](skills/validation-forecast/references/adapters.md)을 따릅니다. 모델 버전, 사용한 입력, 재학습 주기, 튜닝 예산, 실패한 예측을 함께 기록합니다. 새 기능에는 재현 가능한 작은 테스트를 추가합니다.

```bash
python skills/validation-forecast/scripts/test_validation.py
python tools/test_forecast_modes.py
python tools/test_repository.py
```

수치 로직이 바뀌면 변경 전후의 작은 재현 예제와 테스트 결과를 PR에 남깁니다. 지침만 추가했으면 구현 완료라고 쓰지 않습니다. 실제 데이터, API 키, 예측 정답 원장과 대용량 모델은 커밋하지 않습니다.

라이선스와 공개 범위는 저장소 소유자가 결정합니다. 참고 논문이나 외부 코드를 추가할 때는 원문 출처와 사용 조건을 먼저 확인합니다.

계획 스킬이 학습·채점으로 넘어가거나 검증 스킬이 결과에 맞춰 split·window·지표를 바꾸지 않도록 테스트합니다. 공통 evaluator는 validation-forecast에 한 벌만 유지합니다.
