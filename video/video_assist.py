# -*- coding: utf-8 -*-
"""
영상 보조 지표 (Video Assist Metrics)

AI 면접 서비스의 "발표 습관 개선" 보조 코칭용 모듈.
면접 답변 영상에서 시선 처리와 발화 속도를 분석한다.

[매우 중요한 원칙]
- 이 지표들은 면접 점수(5개 역량)에 절대 반영하지 않는다.
- 오직 발표 습관 개선을 위한 보조 코칭 용도로만 사용한다.
- 표정 기반 감정 점수는 공정성 문제로 만들지 않는다.

[실행 환경]
- Python 3.11 또는 3.12 가상환경 필요 (3.13은 mediapipe 미지원이므로 금지)
  생성:  py -3.12 -m venv venv
  설치:  pip install opencv-python mediapipe
"""

import argparse
import sys

import cv2

# mediapipe import 오류 방지: 가상환경이 Python 3.12인지 먼저 확인할 것.
# (3.13에서는 mediapipe가 설치되지 않으므로 ImportError가 발생한다.)
try:
    import mediapipe as mp
except ImportError:
    print("[오류] mediapipe를 불러올 수 없습니다.")
    print("       Python 3.11 또는 3.12 가상환경에서 실행해야 합니다. (3.13 미지원)")
    print("       예) py -3.12 -m venv venv  후  pip install opencv-python mediapipe")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 1. 시선 분석
# ---------------------------------------------------------------------------
class GazeAnalyzer:
    """
    MediaPipe FaceMesh의 홍채 랜드마크로 정면 응시 여부를 판정한다.

    - 왼눈 좌우 끝: 33(바깥), 133(안쪽) / 왼눈 홍채 중심: 468
    - 오른눈 좌우 끝: 362(안쪽), 263(바깥) / 오른눈 홍채 중심: 473
    - 홍채 가로 위치 비율이 0.38~0.62 사이면 "정면 응시"로 판정한다.
    - 전체 분석 프레임 중 정면 응시 비율(%)을 누적 계산한다.
    """

    # 홍채 가로 위치 비율 정면 판정 범위
    FRONT_MIN = 0.38
    FRONT_MAX = 0.62

    def __init__(self):
        # refine_landmarks=True 여야 홍채 랜드마크(468~477)가 활성화된다.
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._total_frames = 0   # 얼굴이 검출된 분석 대상 프레임 수
        self._front_frames = 0   # 그중 정면 응시로 판정된 프레임 수

    @staticmethod
    def _iris_ratio(iris_x, corner_a_x, corner_b_x):
        """홍채 중심이 두 눈끝 사이에서 차지하는 가로 위치 비율(0~1)을 구한다."""
        left = min(corner_a_x, corner_b_x)
        right = max(corner_a_x, corner_b_x)
        width = right - left
        if width <= 0:
            return 0.5  # 비정상 좌표는 중앙으로 간주
        return (iris_x - left) / width

    def process(self, frame_bgr):
        """
        한 프레임을 분석한다.
        정면 응시로 판정되면 True, 아니면 False를 반환한다.
        얼굴 미검출 시 None을 반환한다(누적에서 제외).
        """
        # OpenCV는 BGR, MediaPipe는 RGB를 사용하므로 변환한다.
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(frame_rgb)

        if not result.multi_face_landmarks:
            return None  # 얼굴이 없으면 집계하지 않는다.

        landmarks = result.multi_face_landmarks[0].landmark

        # 정규화 좌표(0~1)에서 가로(x) 값만 사용한다.
        left_iris_x = landmarks[468].x
        left_corner1_x = landmarks[33].x
        left_corner2_x = landmarks[133].x

        right_iris_x = landmarks[473].x
        right_corner1_x = landmarks[362].x
        right_corner2_x = landmarks[263].x

        left_ratio = self._iris_ratio(left_iris_x, left_corner1_x, left_corner2_x)
        right_ratio = self._iris_ratio(right_iris_x, right_corner1_x, right_corner2_x)

        # 양쪽 눈의 평균 비율로 판정한다.
        avg_ratio = (left_ratio + right_ratio) / 2.0
        is_front = self.FRONT_MIN <= avg_ratio <= self.FRONT_MAX

        self._total_frames += 1
        if is_front:
            self._front_frames += 1

        return is_front

    def summary(self):
        """정면 응시 비율(%)을 반환한다. 분석된 프레임이 없으면 0.0."""
        if self._total_frames == 0:
            return 0.0
        return self._front_frames / self._total_frames * 100.0

    def close(self):
        """FaceMesh 리소스를 해제한다."""
        self._face_mesh.close()


# ---------------------------------------------------------------------------
# 2. 발화 속도 분석
# ---------------------------------------------------------------------------
class SpeechRateAnalyzer:
    """
    발화 속도(분당 글자수)를 계산한다.

    실제 서비스에서는 STT 담당자가 인식된 텍스트와 발화 시간을 넘겨준다.
    지금은 샘플값으로 처리한다.
    """

    @staticmethod
    def chars_per_minute(text, duration_sec):
        """글자수 / 시간 * 60 으로 분당 글자수(CPM)를 계산한다."""
        if duration_sec <= 0:
            return 0.0
        char_count = len(text)
        return char_count / duration_sec * 60.0


# ---------------------------------------------------------------------------
# 3. 피드백 생성
# ---------------------------------------------------------------------------
def gaze_feedback(gaze_percent):
    """정면 응시 비율(%)에 대한 코칭 피드백. {level, message, gauge}."""
    if gaze_percent >= 85:
        return {"level": "좋음", "message": "안정적으로 면접관을 응시하고 있어요.",
                "gauge": round(gaze_percent, 1)}
    elif gaze_percent >= 70:
        return {"level": "보통", "message": "대체로 좋지만 시선이 가끔 흔들려요.",
                "gauge": round(gaze_percent, 1)}
    else:
        return {"level": "개선 필요", "message": "시선이 자주 아래로 향해요. 정면을 응시하는 연습을 해보세요.",
                "gauge": round(gaze_percent, 1)}


def speech_feedback(speech_cpm):
    """발화 속도(분당 글자수)에 대한 코칭 피드백(한국어 기준). {level, message, gauge}."""
    if speech_cpm > 330:
        return {"level": "빠름", "message": "말이 다소 빨라요. 조금 천천히 또박또박 말해보세요.",
                "gauge": round(speech_cpm, 1)}
    elif speech_cpm < 200:
        return {"level": "느림", "message": "말이 다소 느려요. 조금 더 또렷하고 빠르게 말해보세요.",
                "gauge": round(speech_cpm, 1)}
    else:
        return {"level": "적정", "message": "발화 속도가 적정해요. 듣기 편한 속도입니다.",
                "gauge": round(speech_cpm, 1)}


def build_feedback(gaze_percent, speech_cpm):
    """시선+발화 보조 지표 코칭 피드백을 함께 반환한다. {gaze, speech}."""
    return {"gaze": gaze_feedback(gaze_percent), "speech": speech_feedback(speech_cpm)}


# ===========================================================================
# 서버 연동용 함수 (유정님: 이 두 함수를 import해서 호출)
# ===========================================================================
def analyze_video(video_path, sample_every=1, with_timeline=True):
    """
    영상 파일에서 시선 보조 지표를 분석한다. (서버에서 호출, GUI 없음)

    Args:
        video_path   : 분석할 영상 파일 경로 (webm/mp4 등)
        sample_every : N프레임마다 1개만 분석 (긴 영상 가속용, 기본 1=전 프레임)
        with_timeline: 시선 이탈 구간 타임라인 포함 여부 (기본 True, 안 쓰면 False)

    Returns:
        {
          "gaze_percent": 88.0,                  # 정면 응시 비율(%)  ← 핵심
          "gaze": {"level","message","gauge"},   # 코칭 피드백
          "frames_analyzed": 300,                # 얼굴 검출된 분석 프레임 수
          "timeline": [{"start_sec": 4.2, "end_sec": 6.1}, ...]  # 시선 이탈 구간(선택)
        }

    ※ 이 값은 면접 점수에 미반영(보조 코칭용). 파일을 못 열면 ValueError.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0  # FPS를 못 얻으면 30으로 가정

    analyzer = GazeAnalyzer()
    away_segments = []
    away_start = None
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if sample_every > 1 and (frame_index % sample_every != 0):
                frame_index += 1
                continue

            is_front = analyzer.process(frame)
            t = frame_index / fps

            if with_timeline:
                if is_front is False:            # 시선 이탈(얼굴 O, 정면 X)
                    if away_start is None:
                        away_start = t
                elif away_start is not None:      # 정면 복귀/얼굴 없음 → 이탈 종료
                    away_segments.append({"start_sec": round(away_start, 1),
                                          "end_sec": round(t, 1)})
                    away_start = None
            frame_index += 1

        if away_start is not None:               # 영상 끝까지 이탈 중이었던 경우
            away_segments.append({"start_sec": round(away_start, 1),
                                  "end_sec": round(frame_index / fps, 1)})
    finally:
        cap.release()
        analyzer.close()

    gaze_percent = analyzer.summary()
    result = {
        "gaze_percent": round(gaze_percent, 1),
        "gaze": gaze_feedback(gaze_percent),
        "frames_analyzed": analyzer._total_frames,
    }
    if with_timeline:
        result["timeline"] = away_segments
    return result


def speech_rate(text, duration_sec):
    """
    발화 속도(분당 글자수)를 계산한다. (서버에서 호출)
    현주님 STT의 text·발화시간을 받아 계산 → 유정님이 응답에 합침.

    Args:
        text         : 인식된 답변 텍스트
        duration_sec : 그 답변을 말한 시간(초)

    Returns:
        {"speech_cpm": 286.0, "speech": {"level","message","gauge"}}
    """
    cpm = SpeechRateAnalyzer.chars_per_minute(text or "", duration_sec or 0)
    return {"speech_cpm": round(cpm, 1), "speech": speech_feedback(cpm)}


# ---------------------------------------------------------------------------
# 4. 메인 실행
# ---------------------------------------------------------------------------
def _try_imshow(window_name, frame):
    """
    GUI가 없는 서버 환경을 대비해 cv2.imshow를 안전하게 호출한다.
    표시에 성공하면 True, GUI를 쓸 수 없으면 False를 반환한다.
    """
    try:
        cv2.imshow(window_name, frame)
        return True
    except cv2.error:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="영상 보조 지표 — 시선 처리/발화 속도 분석 (면접 점수 미반영, 보조 코칭용)"
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="분석할 영상 파일 경로 (지정하지 않으면 웹캠 사용)",
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=10,
        help="웹캠 분석 시간(초). 영상 파일 사용 시에는 무시됨 (기본 10초)",
    )
    args = parser.parse_args()

    # 입력 소스 결정: 영상 파일 또는 웹캠(0번 장치)
    if args.video:
        cap = cv2.VideoCapture(args.video)
        source_desc = f"영상 파일: {args.video}"
    else:
        cap = cv2.VideoCapture(0)
        source_desc = f"웹캠 (약 {args.seconds}초 분석)"

    if not cap.isOpened():
        print(f"[오류] 입력 소스를 열 수 없습니다 → {source_desc}")
        sys.exit(1)

    print(f"[시작] {source_desc}")
    print("       분석 중입니다... (창에서 q 키를 누르면 종료)")

    analyzer = GazeAnalyzer()
    gui_available = True

    # 웹캠 분석 시간 제한을 프레임 수로 환산한다.
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 0:
        fps = 30.0  # FPS 정보를 못 얻으면 30으로 가정
    max_webcam_frames = int(fps * args.seconds) if not args.video else None

    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break  # 영상 끝 또는 읽기 실패

            is_front = analyzer.process(frame)
            frame_index += 1

            # 실시간 화면 표시 (GUI 없는 환경 대비)
            if gui_available:
                label = "FRONT" if is_front else ("NO FACE" if is_front is None else "AWAY")
                cv2.putText(
                    frame, label, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2,
                )
                if _try_imshow("Video Assist (q to quit)", frame):
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                else:
                    gui_available = False  # 한 번 실패하면 이후 표시 시도하지 않음

            # 웹캠 모드에서 지정 시간이 지나면 종료
            if max_webcam_frames is not None and frame_index >= max_webcam_frames:
                break
    finally:
        cap.release()
        analyzer.close()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass

    # --- 결과 집계 ---
    gaze_percent = analyzer.summary()

    # 발화 속도: 실제로는 STT 담당자가 텍스트+발화시간을 넘겨준다.
    # 지금은 샘플값으로 처리한다.
    sample_text = "안녕하세요 저는 성실하고 책임감 있는 지원자입니다 잘 부탁드립니다"
    sample_duration_sec = 12.0
    speech_cpm = SpeechRateAnalyzer.chars_per_minute(sample_text, sample_duration_sec)

    feedback = build_feedback(gaze_percent, speech_cpm)

    # --- 콘솔 출력 ---
    print()
    print("=" * 48)
    print("           영상 보조 지표 분석 결과")
    print("=" * 48)
    print(f"[시선 처리] {feedback['gaze']['level']} "
          f"(정면 응시 {feedback['gaze']['gauge']}%)")
    print(f"            └ {feedback['gaze']['message']}")
    print(f"[발화 속도] {feedback['speech']['level']} "
          f"({feedback['speech']['gauge']}자/분)")
    print(f"            └ {feedback['speech']['message']}")
    print("-" * 48)
    print("※ 이 지표는 면접 점수(5개 역량)에 미반영되며,")
    print("  발표 습관 개선을 위한 보조 코칭 용도로만 사용됩니다.")
    print("=" * 48)


if __name__ == "__main__":
    main()
