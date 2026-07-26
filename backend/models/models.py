from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(10))
    content = Column(Text)
    eval_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    interview_sessions_session_id = Column(String(36), ForeignKey("interview_sessions.session_id"))

    session = relationship("InterviewSession", back_populates="messages")


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