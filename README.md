# 오피넷 2개 주유소 가격 브리핑

알뜰 걸포주유소와 유턴주유소를 기준으로 반경 1km·3km·5km의 가격 순위를
계산하고, ChatGPT 예약 작업이 매일 오전 7시 30분(KST)에 읽을 수 있도록
결과를 GitHub에 저장하는 Python 프로그램입니다.
가격을 변경하는 기능은 전혀 없으며, 조회·비교·의견 제시만 합니다.

## 먼저 알아둘 점

- 사용자가 알려준 걸포주유소 주소의 `김포로`는 실제로는 **금포로**입니다.
- 오피넷 반경 API 입력 좌표는 위·경도가 아니라 KATEC입니다. 설정 파일에는
  읽기 쉬운 WGS84 위·경도를 저장하고, 실행 시 자동으로 KATEC으로 변환합니다.
- 오피넷 Open API는 휘발유·경유·실내등유 가격을 제공합니다.
- **세차비는 오피넷에서 제공하지 않습니다.** `config/carwash_prices.yml`에
  직접 확인한 가격을 입력해야 순위와 전일 변동이 계산됩니다.
- HTML 보고서에는 지도와 1·3·5km 상세 테이블이 함께 들어갑니다.

## 설정된 운영 주유소

| 주유소 | 확인한 도로명 주소 | 위도 | 경도 |
|---|---|---:|---:|
| 알뜰 걸포주유소 | 경기 김포시 금포로 1117-6 | 37.6459844 | 126.7066566 |
| 유턴주유소 | 서울 강서구 남부순환로 57 | 37.5571490 | 126.8098880 |

위치는 `config/stations.yml`에 저장되어 있습니다. 오피넷의 주유소 상호가
바뀌더라도 좌표에서 250m 이내인 가장 가까운 후보를 함께 검사합니다.

## 의견 규칙

5km 범위의 최저가와 운영 주유소 가격 차이를 기준으로 판단합니다.

| 차이 | 의견 |
|---:|---|
| 0~2원 | 유지 |
| 3~9원 | 인하 검토 |
| 10원 이상 또는 대상 가격 미확인 | 긴급 확인 |

최저가 주유소, 운영점과 3원 이상 차이가 나는 주유소, 전일 대비 3원 이상
움직인 주유소, 최저가 주유소가 바뀐 경우를 강조합니다.
동일 가격은 공동 순위이며 순위는 `1, 1, 3` 방식입니다. 기준값은
`config/stations.yml`의 `rules`에서 바꿀 수 있습니다.

## 1. 오피넷 API 키 받기

1. [오피넷 유가정보 API 페이지](https://www.opinet.co.kr/user/custapi/custApiInfo.do)에 접속합니다.
2. `무료 API 이용 신청`을 누르고 가입·신청 절차를 마칩니다.
3. 발급된 인증키를 복사해 둡니다.
4. 반경 내 주유소 API 사용 권한이 활성화되어 있는지 확인합니다.

인증키를 Python 파일이나 GitHub 저장소에 직접 쓰면 안 됩니다.

## 2. GitHub에 올리기

1. GitHub에서 새 **비공개(Private)** 저장소를 만듭니다.
2. 이 폴더의 파일 전체를 저장소 최상위에 올립니다.
3. 저장소의 `Settings` → `Actions` → `General`로 이동합니다.
4. `Workflow permissions`에서 `Read and write permissions`를 선택하고 저장합니다.
   이 권한은 전일 비교용 JSON을 저장소에 다시 기록하는 데 필요합니다.

명령줄을 쓸 경우:

```bash
git init
git add .
git commit -m "Initial Opinet briefing"
git branch -M main
git remote add origin https://github.com/내아이디/내저장소.git
git push -u origin main
```

## 3. GitHub Secret에 API 키 등록

저장소에서 `Settings` → `Secrets and variables` → `Actions` →
`New repository secret`을 차례로 눌러 아래 항목을 등록합니다.

| Secret 이름 | 넣을 값 |
|---|---|
| `OPINET_API_KEY` | 오피넷에서 발급받은 인증키 |

Secret 이름은 대소문자까지 표와 정확히 같아야 합니다.

## 4. 처음 한 번 수동 실행하기

1. GitHub 저장소의 `Actions` 탭을 엽니다.
2. 왼쪽에서 `Daily Opinet briefing`을 누릅니다.
3. `Run workflow` → `Run workflow`를 누릅니다.
4. 실행이 초록색 체크로 끝나는지 확인합니다.
5. 저장소의 `data/latest.json`, `data/status.json`이 생겼는지 확인합니다.

이후 GitHub Actions가 매일 **한국시간 오전 7시 10분** 실행합니다. GitHub의
예약 실행은 서버 사정으로 몇 분 늦게 시작할 수 있습니다.

## 5. ChatGPT 오전 7시 30분 알림 연결

GitHub Actions가 ChatGPT에 직접 알림을 보내는 공식 웹훅은 없습니다. 따라서
다음 구조를 사용합니다.

1. ChatGPT에서 GitHub 앱을 연결합니다.
2. 이 비공개 저장소에 대한 읽기 권한을 허용합니다.
3. ChatGPT에 아래처럼 요청합니다.

   `매일 오전 7시 30분에 <소유자>/<저장소>의 data/status.json과
   data/latest.json을 읽고 두 운영 주유소의 핵심 가격·순위·전일 변화·의견을
   알려줘. status가 error이면 오류 메시지를 알려줘.`

저장소를 실제로 만든 뒤 저장소 이름을 알려주면 이 예약 작업을 함께 설정할 수
있습니다. 이 단계 전에는 ChatGPT가 비공개 저장소의 결과를 읽을 수 없습니다.

## 6. 세차비 입력하기

`config/carwash_prices.yml`을 열어 운영 주유소와 주변 경쟁 주유소의 세차비를
입력합니다. 예:

```yaml
stations:
  geolpo:
    name: "알뜰 걸포주유소"
    latitude: 37.6459844
    longitude: 126.7066566
    price: 5000
  competitor_1:
    name: "경쟁주유소 A"
    latitude: 37.6500000
    longitude: 126.7100000
    price: 6000
```

세차 종류가 여러 개라면 같은 조건(예: 기본 자동세차)을 정해 비교해야 합니다.
가격을 모르는 주유소는 `price: null`로 두면 순위에서 제외됩니다.

## 로컬에서 시험하기

Python 3.12 이상을 권장합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export OPINET_API_KEY="발급키"
python -m opinet_briefing.main
python -m pytest
```

Windows PowerShell에서는 `source ...` 대신 아래를 사용합니다.

```powershell
.\.venv\Scripts\Activate.ps1
$env:OPINET_API_KEY="발급키"
python -m opinet_briefing.main
```

## 저장되는 결과

- `data/latest.json`: 가장 최근 실행 결과. 다음 실행 때 전일 비교 기준으로 사용
- `data/status.json`: 성공 요약 또는 오류 메시지. ChatGPT 알림이 먼저 읽는 파일
- `data/history/YYYY-MM-DD.json`: 날짜별 원본 결과
- `reports/opinet-map-YYYY-MM-DD.html`: 인터랙티브 지도

같은 날짜에 다시 실행하면 그 날짜의 JSON은 최신 실행 결과로 덮어씁니다.
GitHub Actions는 JSON만 저장소에 커밋하고 지도는 텔레그램 전송 및 Actions
artifact로 30일 보관합니다.

## 오류가 날 때

- `401`, 인증 오류: `OPINET_API_KEY`가 맞는지와 API 권한을 확인합니다.
- 텔레그램 `400 Bad Request`: 봇에 `/start`를 보냈는지, chat ID가 맞는지 확인합니다.
- JSON 저장 `git push` 실패: Actions의 `Read and write permissions`를 확인합니다.
- 예약 실행이 안 됨: 저장소 Actions가 활성화되어 있는지 확인합니다.

프로그램 실행 중 오류가 나면 `data/status.json`에 오류 요약을 저장합니다.
ChatGPT 예약 작업은 이 파일을 읽어 오류를 알립니다. 전체 내용은 GitHub
`Actions` 실행 로그에서 확인할 수 있습니다.

## 보안

- API 키는 오직 GitHub Secrets에 보관합니다.
- `.env`는 `.gitignore`에 포함되어 있습니다.
- 로그나 스크린샷에 토큰이 찍히지 않도록 주의하십시오.
- 이 프로그램은 가격 변경 API나 가격 입력 기능을 구현하지 않습니다.
