# 배포 가이드 — GitHub + Hugging Face Spaces + Cloudflare R2

> 이 문서는 본인(개발자) 전용. 자문가에게는 공유 안 함.

## 인프라 구성

```
┌─ GitHub (Private) ─┐
│ jongsuhan417-debug │  ←── 코드 마스터 (백업, 미래 마이그레이션 자유)
│ /wushu             │
└─────────┬──────────┘
          │ git push
          ↓
┌─ HF Spaces (hjs417/wushu) ─┐
│ Docker SDK, CPU 16GB 무료   │
│ Container = Python+Streamlit│
│ Secrets: R2 키, Anthropic   │
└─────────┬───────────────────┘
          │ 영상 IO
          ↓
┌─ Cloudflare R2 (wushu) ─────┐
│ APAC, 10GB 무료              │
│ S3 호환 API                   │
│ presigned URL 1시간 TTL      │
└──────────────────────────────┘
```

---

## 첫 배포 (10~15분)

### 1) GitHub remote 추가

```powershell
cd e:\claudecode\Wushu

# 첫 init이면
git init
git branch -M main

# Remote 등록
git remote add origin https://github.com/jongsuhan417-debug/wushu.git
git remote add hf https://huggingface.co/spaces/hjs417/wushu
```

### 2) 첫 commit + push

```powershell
git add .
git commit -m "Initial: Wushu workbench v0.1 (HF Spaces + R2)"

# GitHub 먼저
git push -u origin main
# (GitHub 사용자명 + Personal Access Token 입력)

# HF Spaces로
git push hf main
# (HF 사용자명 hjs417 + HF Access Token 입력)
```

### 3) HF Spaces 자동 빌드 모니터링

- https://huggingface.co/spaces/hjs417/wushu 페이지 접속
- 상단 "Building" 상태 표시 (Dockerfile 빌드 ~5분 + 모델 다운로드 ~10초)
- 완료되면 Space iframe에 워크벤치 표시
- 영구 URL: `https://hjs417-wushu.hf.space` (또는 `https://huggingface.co/spaces/hjs417/wushu`)

### 4) 자문가에게 URL 전달

```
워크벤치 URL: https://hjs417-wushu.hf.space
좌측 사이드바 상단에서 [中文] 토글 후 [使用指南]부터 봐주세요.
```

---

## 평소 작업 흐름

코드 수정 후:

```powershell
git add .
git commit -m "변경 내용 한 줄"
git push origin main      # GitHub로
git push hf main          # HF로 (자동 재빌드 ~3~5분)
```

또는 한 번에 양쪽:

```powershell
git remote set-url --add --push origin https://github.com/jongsuhan417-debug/wushu.git
git remote set-url --add --push origin https://huggingface.co/spaces/hjs417/wushu
git push origin main      # 양쪽 모두 한 번에
```

---

## 환경 변수 정리

### `.env` (본인 PC, gitignore됨)

```
ANTHROPIC_API_KEY=sk-ant-...
WUSHU_DATA_DIR=./data
WUSHU_DEFAULT_LANG=ko
WUSHU_TRANSLATOR_MODEL=claude-haiku-4-5-20251001
STORAGE_BACKEND=r2
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ENDPOINT=https://616dd6c83d008710f8c2eba3455e5fc2.r2.cloudflarestorage.com
R2_BUCKET=wushu
R2_URL_TTL=3600
HF_TOKEN=hf_... (push 인증용)
```

### HF Spaces Settings (Secrets/Variables)

**Secrets** (5개):
- `ANTHROPIC_API_KEY`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

**Variables** (5개):
- `STORAGE_BACKEND=r2`
- `R2_ENDPOINT=https://616dd6c83d008710f8c2eba3455e5fc2.r2.cloudflarestorage.com`
- `R2_BUCKET=wushu`
- `WUSHU_DEFAULT_LANG=ko`
- `WUSHU_TRANSLATOR_MODEL=claude-haiku-4-5-20251001`

> ⚠️ HF Spaces의 `WUSHU_DATA_DIR`는 Dockerfile에서 `/data`로 자동 설정. 등록 X.

---

## 로컬 테스트 (배포 전 검증)

```powershell
# venv 활성화
.\.venv\Scripts\Activate.ps1

# 로컬에서도 R2 사용 (.env에 키 있으니 자동)
python scripts/init_db.py
streamlit run apps/workbench/app.py
```

또는 로컬 디스크 사용:
```powershell
$env:STORAGE_BACKEND="local"
streamlit run apps/workbench/app.py
```

---

## R2 사용량 모니터링

- Cloudflare 대시보드 → R2 → wushu bucket → Metrics
- 무료 한도: 10GB 저장 + 월 1M class A + 10M class B
- 자문가 영상이 폼당 3 테이크 × 50MB = 150MB → 폼 60개 가능 (충분)

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| HF 빌드 실패 | requirements.txt 누락 | `git status`로 확인 후 push |
| MediaPipe 에러 | 모델 다운로드 실패 | Persistent Storage 마운트 확인 |
| 영상 재생 안 됨 | presigned URL 만료 | `R2_URL_TTL` 늘리기 (기본 3600초) |
| 번역 동작 안 함 | API 키 누락 | HF Secrets에 ANTHROPIC_API_KEY 확인 |
| R2 401/403 | 토큰 권한 | R2 토큰을 Object Read & Write로 재발급 |

---

## 다음 단계 (Stage 2 진입 시)

- VPS로 옮기는 경우: 환경변수 그대로, R2도 그대로 사용 가능
- 학생 데이터 들어오는 경우: 영상은 클라이언트(폰) MediaPipe로 처리, 서버엔 포즈 JSON만
- 도메인 연결: HF Pro $9/월 또는 VPS + Cloudflare Tunnel
