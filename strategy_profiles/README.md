# Research Strategy Profiles

이 디렉터리는 고정된 Common Engine에 주입할 Research Strategy Profile을 관리한다.

## 책임

- Market, Filter, Sizing, BUY Guard, BUY, SELL 설정을 Version별로 관리한다.
- Backtest Policy와 Metrics 설정을 전략 실행 설정과 함께 추적한다.
- Common Package Version과 Common Strategy Version을 Metadata에 기록한다.
- 실제 실행에서는 Profile Override와 Common Default를 병합한 Resolved Config를 사용한다.

## 제외 범위

- Backtest 시작일과 Decision 기준일은 Run Input으로 관리한다.
- REPORT_CONFIG는 거래 결과가 아닌 분석과 표현 설정이므로 포함하지 않는다.
- Profile 상태는 운영 자동 승격이나 Champion 지정을 의미하지 않는다.

## Baseline

- RSCFG-0001은 Common Package 1.0.0 기준 Baseline Profile이다.
- Common에 명시된 Config와 BUY Guard 함수 내부의 숨은 Default를 전개한다.
- Decimal 기반 값은 정밀도 보존을 위해 JSON 문자열로 저장한다.
- Schema와 Unknown Key 강제 검증은 후속 Profile Validator에서 수행한다.
