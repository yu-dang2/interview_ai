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
    """
    면접 1건의 최종 결과.

    예전에는 리포트 전체를 json.dumps 로 feedback 컬럼 하나에 넣었다. 그러면
    "평균 정면 응시율", "역량별 평균" 같은 집계를 SQL 로 할 수 없고, 마이페이지
    기록 표를 만들려면 행마다 JSON 을 파싱해야 한다. 그래서 화면이 쓰는 값은
    전부 컬럼으로 편다.

    raw_report 에 원본 JSON 을 남기는 이유: 컬럼 매핑이 틀렸을 때 재계산할 수 있고,
    agent 쪽 리포트 키가 바뀌어도 과거 데이터를 복구할 수 있다.
    """

    __tablename__ = "interview_results"

    result_id = Column(Integer, primary_key=True, autoincrement=True)

    # 점수 3종. total_score 는 가중 합산한 최종 점수다.
    # (RESUME_WEIGHT × resume_score + INTERVIEW_WEIGHT × interview_score)
    # 예전에는 여기에 면접 점수를 그대로 넣어서 /result 응답의 total_score 와 값이 달랐다.
    resume_score = Column(Integer, default=0)
    interview_score = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    grade = Column(String(5))      # report_generator 가 내주는 등급 (A+, B+ ...)

    # 5개 역량 점수. 레이더 차트와 집계에 쓴다.
    logic_score = Column(Integer, default=0)
    communication_score = Column(Integer, default=0)
    expertise_score = Column(Integer, default=0)
    attitude_score = Column(Integer, default=0)
    problem_solving_score = Column(Integer, default=0)

    # 종합 총평 3종
    summary_strength = Column(Text)
    summary_improvement = Column(Text)
    summary_recommendation = Column(Text)

    # 집계 대상이 아니라 JSON 문자열 그대로 둔다.
    eval_keywords = Column(Text)
    weakness_areas = Column(Text)

    raw_report = Column(Text)      # report_generator 원본 JSON (구 feedback 컬럼)

    created_at = Column(DateTime, default=func.now())
    # 세션당 결과는 1건이다. uselist=False 관계도 그 전제이므로 DB 로 강제한다.
    interview_sessions_session_id = Column(
        String(36), ForeignKey("interview_sessions.session_id"), unique=True
    )

    session = relationship("InterviewSession", back_populates="result")
    question_feedbacks = relationship(
        "InterviewQuestionFeedback",
        back_populates="result",
        cascade="all, delete-orphan",
        order_by="InterviewQuestionFeedback.question_number",
    )


class InterviewQuestionFeedback(Base):
    """
    질문 하나에 대한 복기·교정. 예전에는 리포트 JSON 안의 question_feedbacks 배열이었다.

    행으로 펴야 "평균 점수", "가장 낮은 점수의 질문" 같은 조회가 가능하다.
    """

    __tablename__ = "interview_question_feedbacks"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    # 리포트에 번호가 없어서 백엔드가 리스트 순서대로 1부터 매긴다.
    question_number = Column(Integer)
    question = Column(Text)
    user_answer = Column(Text)
    score = Column(Integer, default=0)
    improved_answer = Column(Text)
    interview_results_result_id = Column(Integer, ForeignKey("interview_results.result_id"))

    result = relationship("InterviewResult", back_populates="question_feedbacks")