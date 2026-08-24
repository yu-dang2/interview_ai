"""
mediapipe 격리 venv 에서 실행되는 영상 분석 러너.

영상 분석(mediapipe)은 protobuf 4.25 를 요구해, 백엔드 프로세스(protobuf 7·chromadb)와
같은 파이썬에 공존할 수 없다. 그래서 백엔드(video_service.analyze)는 이 스크립트를
mediapipe 가 설치된 별도 venv 파이썬으로 subprocess 실행하고, stdout 의 결과 JSON 만
받아서 쓴다.

실행:
    <mp_venv>/python video/analyze_runner.py <영상경로> [--sample-every N] [--with-timeline]

출력(stdout 마지막 줄, 한 줄 JSON):
    성공: {"ok": true, "result": {...analyze_video 반환...}}
    실패: {"ok": false, "error_type": "value|other", "message": "..."}

mediapipe import 자체가 실패하면 video_assist 가 sys.exit(1) 을 부르고 이 스크립트도
비정상 종료한다. 백엔드는 그 exit code(≠0)로 "분석 모듈 로드 실패"를 구분한다.
cv2·mediapipe 로그가 stdout 앞부분에 섞일 수 있어, 백엔드는 마지막 JSON 줄만 파싱한다.
"""

import argparse
import json
import os
import sys

# 이 스크립트가 있는 video/ 를 경로에 넣어 video_assist 를 형제 모듈로 import 한다.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# stdout 을 UTF-8 로 고정한다. 백엔드는 결과를 UTF-8 로 읽는데, 이 프로세스가 실행
# 환경 로캘(예: Windows cp949)로 한글 JSON 을 내보내면 백엔드 디코딩이 깨진다
# (0xc1 invalid start byte). 로캘과 무관하게 UTF-8 로 쓰도록 강제한다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _emit(payload: dict) -> None:
    # 결과는 반드시 마지막 한 줄에 둔다. default=float 로 numpy 스칼라도 직렬화한다.
    sys.stdout.write("\n" + json.dumps(payload, ensure_ascii=False, default=float) + "\n")
    sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="면접 영상 시선 분석 러너")
    parser.add_argument("video_path")
    parser.add_argument("--sample-every", type=int, default=1)
    parser.add_argument("--with-timeline", action="store_true")
    args = parser.parse_args()

    # mediapipe 미설치면 여기서 video_assist 가 sys.exit(1) → 스크립트 종료(code 1).
    from video_assist import analyze_video

    try:
        result = analyze_video(
            args.video_path,
            sample_every=args.sample_every,
            with_timeline=args.with_timeline,
        )
    except ValueError as e:
        # 파일을 못 열었을 때(깨진 파일·코덱). 백엔드에서 ValueError 로 되살린다.
        _emit({"ok": False, "error_type": "value", "message": str(e)})
        return
    except Exception as e:  # noqa: BLE001  (러너 경계에서 모든 예외를 JSON 으로 회수)
        _emit({"ok": False, "error_type": "other", "message": str(e)})
        return

    _emit({"ok": True, "result": result})


if __name__ == "__main__":
    main()
