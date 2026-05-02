---
title: Wushu Workbench
emoji: 🥋
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 8501
pinned: false
short_description: AI Wushu motion evaluation workbench (CWA Duan Wei System)
---

# 우슈 평가 워크벤치 (Wushu Evaluation Workbench)

AI 모션 인식 기반 우슈 품세 자동 채점 시스템 — 자문가 검증·튜닝용 내부 도구.

> **상태**: v0.1 — 개발 단계 워크벤치. CWA 段位制 기반.

---

## 빠른 시작 (Windows + PowerShell)

```powershell
# 1) 가상환경
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) 의존성 설치 (Python 3.10 ~ 3.12 권장)
pip install -r requirements.txt

# 3) 환경변수
Copy-Item .env.example .env
# .env 열어서 ANTHROPIC_API_KEY 채우기

# 4) MediaPipe Pose 모델 다운로드 (~9MB, 1회만)
python scripts/download_models.py

# 5) 데이터베이스 초기화
python scripts/init_db.py

# 6) 워크벤치 실행
streamlit run apps/workbench/app.py
```

브라우저가 자동으로 `http://localhost:8501` 열림.

## 자문가에게 공유 (원격 접속)

본인 PC에서 워크벤치를 띄운 채로, Cloudflare Tunnel로 임시 공개 URL을 발급:

```powershell
# cloudflared 설치 (한 번만)
winget install --id Cloudflare.cloudflared

# 터널 실행 (앱이 떠 있는 동안 같이 실행)
cloudflared tunnel --url http://localhost:8501
```

출력에 나오는 `https://xxxxx.trycloudflare.com` URL을 자문가에게 위챗으로 전달.
인증 없는 단순 URL이므로 외부 채널엔 공유 금지.

## 디렉터리 구조

```
.
├── apps/workbench/           # Streamlit 앱
│   ├── app.py                # 진입점 (st.navigation)
│   └── pages/                # 각 페이지 모듈
├── core/                     # 도메인 로직 (포즈/채점/번역)
├── data/
│   ├── stance_dictionary.yaml   # 보형(步型) 사전
│   ├── forms.yaml               # 폼 카탈로그
│   ├── i18n/                    # UI 다국어 문자열
│   ├── videos/                  # 업로드된 영상 (gitignore)
│   ├── poses/                   # 추출된 포즈 시퀀스 JSON
│   ├── references/              # 평균 템플릿
│   └── workbench.db             # SQLite (gitignore)
├── scripts/init_db.py
└── DESIGN.md / WORKBENCH.md  # 설계 문서
```

## 기술 스택

- **포즈 추정**: MediaPipe Pose (33 keypoints)
- **시각화**: OpenCV 오버레이 → MP4
- **채점**: DTW 시간정렬 + 관절 각도 비교
- **UI**: Streamlit (멀티페이지, 한·중 토글)
- **번역**: Claude API (자유 텍스트 양방향)
- **저장**: SQLite + 파일시스템

## 페이지 구성

| 페이지 | 역할 | 주 사용자 |
|---|---|---|
| 🏠 홈 | 폼 상태, 통계, 빠른 시작 | 둘 다 |
| 📖 사용 가이드 | 자문가용 상세 매뉴얼 (中文) | 자문가 |
| 🎥 기준 영상 스튜디오 | 자문가 시범 영상 등록 | 자문가 |
| 🧪 테스트 랩 | 변형 영상 → AI 반응 검증 | 자문가 + 본인 |
| 📋 폼 카탈로그 | 폼 추가·수정·삭제 | 본인 |

좌측 사이드바 상단의 🇰🇷 한국어 / 🇨🇳 中文 버튼으로 언어 전환.

## 다음 단계

1. 자문가에게 워크벤치 URL 위챗으로 공유 → **사용 가이드** 페이지부터 안내
2. 자문가가 **기준 영상 스튜디오**에서 초급 장권 시범 영상 1편 업로드
3. 자문가가 **테스트 랩**에서 변형 영상으로 AI 반응 확인 → 판정 라벨링
4. 누적된 판정 데이터로 임계값 튜닝 → 회귀 테스트 검증
5. 폼 1단 → 2단 → 3단 확장

자세한 설계와 결정사항은 [WORKBENCH.md](WORKBENCH.md) 참고.
