# 우슈 평가 워크벤치 — 설계 문서 (v0.1)

> 본 문서는 [DESIGN.md](DESIGN.md) 의 후속이며, **현재 구현된 워크벤치(Stage 1 도구)** 의 구조·결정사항·코드 매핑을 정리합니다.

---

## 1. 단계 정의

이 워크벤치는 **Stage 1 — 자문가 검증·튜닝용 내부 도구**입니다.
학생 데이터는 들어오지 않습니다. 자문가가 본인 영상으로 변형 테스트를 하고,
AI 반응을 판정 라벨링하는 회귀 테스트 도구로 동작합니다.

| Stage | 산출물 | 사용자 | 본 워크벤치 위치 |
|-------|--------|--------|------------------|
| 0 | 시범 영상 1편 + 수동 채점 | 본인 + 자문가 | (이전 단계) |
| **1** | **본 워크벤치** | **본인 + 자문가** | **현재 위치** |
| 2 | 도장 베타 (학생 5~10명) | 위 + 학생 | 다음 |
| 3 | 모바일 앱 + 위챗 미니 | 위 + 중국 바이어 | 미래 |

---

## 2. 핵심 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 인증 | 없음 (랜덤 URL만) | 사용자 둘, Cloudflare Tunnel + 위챗 공유로 충분 |
| 언어 | 한↔중 토글 (사이드바) | 자문가는 중국어, 본인은 한국어 |
| 자유 텍스트 번역 | Claude API + 디스크 캐시 | 양방향 자동 번역, 비용 무시 가능 |
| DB | SQLite (단일 파일) | 두 명 도구에 PG 오버킬 |
| 영상 처리 | 동기 + 진행바 (st.status) | 1분 영상 30~60초, 비동기 큐 불필요 |
| 호스팅 | 본인 PC + Cloudflare Tunnel | Stage 1 합리적, Stage 2에서 VPS로 이전 |
| 나란히 비교 뷰 | v0.2 이후 | 현재는 단일 영상 + 스켈레톤 오버레이 |
| "검수 큐"가 아니라 "테스트 랩" | 회귀 테스트 UI | 학생 데이터 없는 단계의 본질 |

---

## 3. 페이지 구조

```
워크벤치 (단일 URL, 멀티페이지 Streamlit)
├── 🏠 홈                     - 대시보드, 통계, 빠른 시작 가이드, 최근 활동
├── 📖 사용 가이드            - 중국인 자문가용 상세 매뉴얼 (中文 우선)
├── 🎥 기준 영상 스튜디오    - 자문가 시범 영상 등록 → 캐노니컬 템플릿
├── 🧪 테스트 랩              - 변형 영상 → AI 반응 확인 → 판정 라벨링
└── 📋 폼 카탈로그            - 폼 추가·수정·삭제, 단별 분류
```

**자문가 메인 동선**: 가이드 (1회) → 기준 영상 스튜디오 (반복) → 테스트 랩 (반복)
**본인 메인 동선**: 홈 → 폼 카탈로그 (관리) → 테스트 랩 (검증) → 임계값 튜닝 (코드)

---

## 4. 디렉터리 구조 & 파일 매핑

```
e:/claudecode/Wushu/
├── README.md
├── DESIGN.md                            # 전체 시스템 설계 (앱·서비스 비전)
├── WORKBENCH.md                         # 본 문서 (Stage 1 도구 설계)
├── requirements.txt
├── .env.example
├── .streamlit/config.toml               # 테마(중국홍 + 크림 + 골드)
│
├── data/
│   ├── stance_dictionary.yaml           # 보형 사전 (마보/궁보/허보/복보/헐보)
│   ├── forms.yaml                       # 폼 카탈로그 (1·2·3단)
│   ├── i18n/
│   │   ├── ko.yaml                      # 한국어 UI 문자열
│   │   └── zh.yaml                      # 중국어 UI 문자열
│   ├── workbench.db                     # SQLite (자동 생성, gitignore)
│   ├── translation_cache.json           # 번역 캐시 (자동 생성)
│   ├── videos/{references,tests}/       # 업로드 영상 (gitignore)
│   ├── poses/{references,tests}/        # 추출된 포즈 시퀀스 JSON
│   └── renders/{references,tests}/      # 스켈레톤 오버레이 영상
│
├── core/
│   ├── paths.py                         # 경로 상수, ensure_dirs()
│   ├── i18n.py                          # t() 헬퍼, 언어 토글 위젯
│   ├── db.py                            # SQLite 스키마 + CRUD
│   ├── pose_extractor.py                # MediaPipe → 포즈 시퀀스 JSON
│   ├── visualizer.py                    # 스켈레톤 오버레이 mp4 생성
│   ├── scorer.py                        # 관절 각도 + DTW 정렬 + 채점
│   ├── stance_detector.py               # 보형 분류 (각도 휴리스틱)
│   └── translator.py                    # Claude API 자유텍스트 번역
│
├── apps/workbench/
│   ├── app.py                           # Streamlit 진입점, st.navigation
│   ├── _ui.py                           # 공통 UI 헬퍼 (hero, pill, card, CSS)
│   └── pages/
│       ├── home.py
│       ├── guide.py                     # 중국어 상세 가이드
│       ├── reference_studio.py
│       ├── test_lab.py
│       └── forms_catalog.py
│
└── scripts/
    └── init_db.py                       # DB 초기화 + forms.yaml 시드
```

---

## 5. 데이터 모델 (SQLite)

```sql
forms (
  id, dan_level, name_ko, name_zh, name_en,
  duration_sec_estimate, description_ko, description_zh,
  primary_stances (JSON), status (draft|recorded|ready),
  created_at, updated_at
)

reference_takes (
  id, form_id (FK), take_number,
  video_path, pose_path, overlay_path,
  duration_sec, self_rating, notes, notes_lang,
  created_at
)

tests (
  id, form_id (FK),
  video_path, pose_path, overlay_path,
  intent, intent_lang, expected (catch|pass|either),
  tags (JSON),
  ai_score, ai_issues (JSON), detected_stances (JSON),
  verdict (pending|correct|missed|wrong),
  comment, comment_lang,
  created_at
)
```

ON DELETE CASCADE: 폼 삭제 시 takes/tests 자동 정리. **단 디스크 파일은 남음** — v0.2에 청소 스크립트 추가 권장.

---

## 6. 처리 파이프라인

### 6.1 기준 영상 등록
```
영상 업로드 (mp4, ≤500MB)
    ↓ data/videos/references/{form_id}/{uuid}.mp4
[MediaPipe Pose, complexity=1]
    ↓ 33 keypoints × N frames
data/poses/references/{form_id}/{uuid}.json
    ↓
[OpenCV 스켈레톤 오버레이]
    ↓ 점·선 그리기, 각 관절 색상 (현재는 모두 neutral)
data/renders/references/{form_id}/{uuid}.mp4
    ↓
DB에 take 레코드 추가, take_number 증분
폼 상태 draft → recorded 전이
```

### 6.2 테스트 채점
```
영상 업로드
    ↓
[포즈 추출, 동일]
    ↓
[캐노니컬 기준 선정] = self_rating 최고 take, 없으면 take #1
    ↓
[채점 엔진]
    1. 각 프레임 → 6개 핵심 관절 각도
    2. DTW로 시간 정렬 (test ↔ reference)
    3. 정렬 페어별 각도 차이 계산
    4. 평균 차이 → 0~10점 환산 (10 - mean/5)
    5. 25° 이상 차이 → 이슈로 마킹
    6. 동일 관절 중복 제거 → 상위 5개 이슈
    ↓
[보형 감지] 각 프레임 보형 분류 (마보/궁보/허보/복보)
    ↓
[스켈레톤 오버레이] 색상 = 관절별 심각도 (ok/warn/bad)
    ↓
DB에 test 레코드 추가, verdict='pending'
```

### 6.3 회귀 테스트
- 모든 기존 테스트를 같은 채점 엔진에 다시 통과
- 임계값/룰 변경 후 효과 검증

---

## 7. 채점 알고리즘 디테일

### 7.1 관절 각도 계산
3D 코사인 — `acos(dot(v1, v2) / (|v1|·|v2|))`. MediaPipe의 z 좌표 포함.

### 7.2 모니터링 관절 (6개)
좌·우 무릎, 좌·우 엉덩이, 좌·우 팔꿈치.

### 7.3 DTW 비용
프레임 간 거리 = 6개 관절 각도 차이의 평균 (None인 관절은 30° 페널티).

### 7.4 점수 환산
`score = max(0, 10 - mean_cost / 5)`. 평균 5° 차이 ≈ 9점, 25° ≈ 5점.

### 7.5 임계값 (v0.1 기본값 — 자문가 검증 후 조정)
- `JOINT_TOLERANCE_DEG = 15` — ok / warn 경계
- `JOINT_TOLERANCE_DEG * 2 = 30` — warn / bad 경계
- `ISSUE_THRESHOLD_DEG = 25` — 이슈로 보고할 최소 차이

### 7.6 성능 가드
DTW가 O(N×M)이라 영상이 길면 느림. `DTW_MAX_FRAMES = 600`으로 다운샘플링.

---

## 8. 다국어 시스템

### 8.1 UI 문자열
`data/i18n/{ko,zh}.yaml` — 키 구조 동일, 두 파일 동시에 추가.

```python
from core.i18n import t
t("nav.home")                      # "홈" or "主页"
t("forms.dan_level", level=1)      # "1단" or "1段"
```

### 8.2 자유 텍스트
- 자문가 입력 (zh) → 본인이 한국어로 보면 자동 번역
- 본인 입력 (ko) → 자문가가 중국어로 보면 자동 번역
- Claude Haiku 4.5 사용, 우슈 용어(马步, 弓步 등)는 보존 지시
- SHA256 해시 키로 디스크 캐시 → 재번역 비용 0

### 8.3 언어 토글
사이드바 상단에 두 버튼 — 클릭 즉시 `st.rerun()`. 모든 페이지가 새 언어로 다시 렌더.

---

## 9. UX 디자인 결정

| 요소 | 결정 |
|------|------|
| 색상 팔레트 | 중국홍 #C0392B (primary), 크림 #FAF7F2 (배경), 다크브라운 #1F1B16 (사이드바) |
| 타이포 | 시스템 sans-serif 우선 — Pretendard / Noto Sans KR / Noto Sans SC |
| 히어로 | 그라데이션 카드 (각 페이지 상단), eyebrow + title + subtitle |
| 카드 | st.container(border=True), 1px 베이지 보더, 12px radius |
| 상태 표시 | 색상 pill (status: draft/recorded/ready, severity: ok/warn/bad/info) |
| 진행 표시 | st.status (단계별 라벨) + st.progress (퍼센트) |
| 사이드바 | 다크 브라운, 브랜드 + 언어 토글 + 자동 nav |

---

## 10. 알려진 한계 & v0.2 백로그

### v0.1 한계
- 단일 카메라 2D 포즈 (회전·도약 정확도 낮음)
- 캐노니컬 기준 = 단일 take (다중 take 평균 미적용)
- 나란히 비교 뷰 없음 (단일 오버레이만)
- 음성 메모 미지원
- 폼 삭제 시 디스크 파일 청소 안 됨
- @st.dialog 타이틀바는 영문 고정

### v0.2 우선순위
1. **다중 take 평균 템플릿** (`reference_builder.py` 신설)
2. **나란히 비교 뷰** (기준 vs 테스트 동시 재생)
3. **음성 메모** (Whisper 로컬 또는 OpenAI API)
4. **자동 구간 분할** (동작 에너지 최소점 검출)
5. **임계값/룰 백오피스 편집 UI**
6. **회귀 테스트 결과 다이프** (전 vs 후 비교)
7. **폼 삭제 시 파일 청소**

### v1.0 (Stage 2 진입)
- 학생 영상 업로드 분리 (별도 학생 앱)
- 인증 추가 (간단 비밀번호)
- VPS 이전 (24시간 가동)
- 검수 큐 페이지 신설 (학생 attempt 검수)

---

## 11. 자문가 피드백 루프 (이 도구의 본질)

```
[자문가]                            [본인]
  ↓                                    ↓
변형 영상 업로드                      코드 임계값/룰 보유
  ↓                                    ↑
AI 채점 결과 확인                       │
  ↓                                    │
판정 클릭 (correct/missed/wrong)       │
  ↓                                    │
DB에 라벨 누적 ─────────── 매주 ────────┤
  ↓                                    │
자유 코멘트 (中文)                     │
  ↓                                    │
Claude API 번역 (→ ko)  ───────────── 본인 확인 → 코드 조정
  ↓                                    │
회귀 테스트 (전체 다시 채점) ─────────┘
```

→ 워크벤치는 **데이터 수집 + 회귀 검증 + 양방향 의사소통** 세 가지를 동시에 해결.

---

## 12. 다음 행동

1. `pip install -r requirements.txt` (Python 3.10–3.12)
2. `python scripts/init_db.py`
3. `streamlit run apps/workbench/app.py`
4. 자문가에게 가이드 페이지(`/guide`) URL 위챗으로 공유
5. 자문가가 초급 장권 시범 영상 1편 업로드 → 첫 데이터 수집 시작
