from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    roll_no = Column(String, unique=True, index=True, nullable=False)
    attendance_code = Column(String, unique=True, nullable=False)

    attendance_records = relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Boolean, nullable=False, default=True)

    student = relationship("Student", back_populates="attendance_records")
