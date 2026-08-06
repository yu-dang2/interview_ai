from sqlalchemy import Column, Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(50))
    email = Column(String(100), unique=True)
    password = Column(String(200))
    created_at = Column(DateTime, default=func.now())

    resumes = relationship("Resume", back_populates="user")
    jds = relationship("JD", back_populates="user")
    sessions = relationship("InterviewSession", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"

    resume_id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())
    users_user_id = Column(Integer, ForeignKey("users.user_id"))

    user = relationship("User", back_populates="resumes")
    sessions = relationship("InterviewSession", back_populates="resume")


class JD(Base):
    __tablename__ = "jds"

    jd_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200))
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())
    users_user_id = Column(Integer, ForeignKey("users.user_id"))

    user = relationship("User", back_populates="jds")
    sessions = relationship("InterviewSession", back_populates="jd")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id = Column(String(36), primary_key=True)  # UUID
    status = Column(String(20), default="active")
    persona = Column(String(50))
    jd_content = Column(Text)
    follow_up_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    users_user_id = Column(Integer, ForeignKey("users.user_id"))
    resumes_resume_id = Column(Integer, ForeignKey("resumes.resume_id"))
    jds_jd_id = Column(Integer, ForeignKey("jds.jd_id"))

    user = relationship("User", back_populates="sessions")
    resume = relationship("Resume", back_populates="sessions")
    jd = relationship("JD", back_populates="sessions")
    messages = relationship("InterviewMessage", back_populates="session")
    result = relationship("InterviewResult", back_populates="session", uselist=False)
    videos = relationship("InterviewVideo", back_populates="session")


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(10))
    content = Column(Text)
    eval_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    interview_sessions_session_id = Column(String(36), ForeignKey("interview_sessions.session_id"))

    session = relationship("InterviewSession", back_populates="messages")


class InterviewVideo(Base):
    """
    면접 영상 1건과 그 시선 분석 결과.

    소유자는 세션(interview_sessions.users_user_id)을 따라간다. 여기에 users_user_id 를
    또 두면 두 곳이 어긋날 수 있어 조인으로 확인한다.

    시선 지표는 JSON 문자열이 아니라 컬럼으로 편다. 나중에 "평균 정면 응시율" 같은 집계를
    하려면 컬럼이어야 한다. 발화 속도(speech_rate)는 STT 발화시간 경로가 정해지지 않아
    아직 컬럼을 만들지 않았다.

    ※ 이 지표는 면접 점수(5개 역량)에 반영하지 않는다. 그래서 interview_results 와 무관하다.
    """

    __tablename__ = "interview_videos"

    video_id = Column(Integer, primary_key=True, autoincrement=True)

    # 저장소 키. 로컬은 VIDEO_STORAGE_DIR 기준 파일명, S3 전환 시 오브젝트 키가 그대로 들어간다.
    storage_key = Column(String(255), nullable=False)
    content_type = Column(String(100))
    size_bytes = Column(Integer)

    # analyzing → done / failed. 분석이 백그라운드라 프론트가 이 값을 폴링한다.
    # 값 표기는 video/README.md 의 인터페이스 계약을 따른다.
    status = Column(String(20), default="analyzing")
    error_message = Column(Text)   # status=failed 일 때의 사유

    gaze_percent = Column(Float)       # 정면 응시 비율(%)
    gaze_level = Column(String(20))    # 좋음 / 보통 / 개선 필요
    gaze_message = Column(Text)        # 코칭 문구
    frames_analyzed = Column(Integer)  # 얼굴이 검출된 분석 프레임 수

    created_at = Column(DateTime, default=func.now())
    analyzed_at = Column(DateTime)

    interview_sessions_session_id = Column(String(36), ForeignKey("interview_sessions.session_id"))

    session = relationship("InterviewSession", back_populates="videos")


class InterviewResult(Base):
    __tablename__ = "interview_results"

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    total_score = Column(Integer, default=0)
    feedback = Column(Text)
    eval_keywords = Column(Text)   # JSON 문자열로 저장
    weakness_areas = Column(Text)  # JSON 문자열로 저장
    created_at = Column(DateTime, default=func.now())
    interview_sessions_session_id = Column(String(36), ForeignKey("interview_sessions.session_id"))

    session = relationship("InterviewSession", back_populates="result")