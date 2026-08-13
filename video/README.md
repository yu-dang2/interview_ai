# 영상 보조 지표 (Video Assist)

면접 답변 영상에서 **시선 처리 + 발화 속도**를 분석하는 보조 코칭 모듈.

> ⚠️ **원칙**: 이 지표는 면접 점수(5개 역량)에 **미반영**입니다. 발표 습관 개선을 위한 **보조 코칭 전용**이며, 표정·감정 분석은 하지 않습니다(공정성).

## 구성
| 파일 | 용도 | 담당 |
|---|---|---|
| `video_assist.py` | 영상 분석 모듈 (`analyze_video`, `speech_rate`) | 유정님: 서버에서 import |

> 웹캠 녹화 컴포넌트(`webcam_recorder.html`)는 지원님이 `frontend/pages/04_면접_진행.py`에
> 인라인으로 직접 구현하여 대체했습니다. (카메라 선택 로직은 지원님 통합 시 반영 예정)

## 설치 (분석 모듈)
Python **3.11 또는 3.12** 필요 (3.13은 mediapipe 미지원):
```bash
pip install opencv-python mediapipe==0.10.21
```
> ⚠️ **Windows 주의**: mediapipe는 한글 경로에서 로드 실패(`.binarypb` 오류) → venv를 **ASCII 경로**에 만드세요 (예: `C:\mp_venv`).
> `mediapipe` 버전은 **0.10.21로 고정** (최신은 legacy solutions API가 제거됨).

## 사용 (유정님 — 서버 연동)
```python
from video.video_assist import analyze_video, speech_rate

# 1) 시선 분석 (업로드된 영상 파일)
gaze = analyze_video("interview_123.webm")
# → {
#     "gaze_percent": 88.0,                     # 정면 응시 비율(%)  ← 핵심
#     "gaze": {"level","message","gauge"},      # 코칭 피드백
#     "frames_analyzed": 300,
#     "timeline": [{"start_sec": 4.2, "end_sec": 6.1}, ...]  # 시선 이탈 구간(선택)
#   }

# 2) 발화 속도 (현주님 STT의 text·발화시간을 받아 계산)
sp = speech_rate(stt_text, duration_sec=12.5)
# → { "speech_cpm": 286.0, "speech": {"level","message","gauge"} }
```

## 전체 인터페이스 (영상 흐름)
```
[예진 → 유정] 분석 함수 (import 호출)
  analyze_video(영상경로)          → { gaze_percent, gaze, frames_analyzed, timeline }
  speech_rate(text, duration_sec) → { speech_cpm, speech }

[지원 → 유정] 영상 업로드
  POST /interview/{id}/video   (webm 파일)

[유정 → 지원] 분석 결과 조회
  GET /interview/{id}/video-metrics
  → { status: "analyzing"|"done", gaze_percent, speech_cpm, gaze, speech, video_url }
    ※ status로 "분석 중/완료" 구분 (지원님 폴링)

[유정 → 지원] 마이페이지 영상 목록
  GET /mypage/videos → [{ interview_id, date, thumbnail, gaze_percent }, ...]
```
> 영상 지표는 **점수 계산과 분리된 별도 필드**로 전달 (점수에 안 섞이게).
> `timeline`(시선 이탈 구간)은 **선택** — 다시보기 마커를 넣을 때만 사용.
