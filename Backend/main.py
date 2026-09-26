import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import date as date_type
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models


if os.getenv("RENDER") == "true":
    if len(os.getenv("ATTENDANCE_ADMIN_PASSWORD", "")) < 12:
        raise RuntimeError(
            "Set ATTENDANCE_ADMIN_PASSWORD to a password with at least 12 characters."
        )
    if not os.getenv("ATTENDANCE_TOKEN_SECRET"):
        raise RuntimeError("Set ATTENDANCE_TOKEN_SECRET in the deployment environment.")


def initialize_database():
    Base.metadata.create_all(bind=engine)

    student_columns = {
        column["name"] for column in inspect(engine).get_columns("students")
    }
    with engine.begin() as connection:
        if "attendance_code" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN attendance_code VARCHAR")
            )

        students_without_code = connection.execute(
            text(
                "SELECT id FROM students "
                "WHERE attendance_code IS NULL OR attendance_code = ''"
            )
        ).all()
        for (student_id,) in students_without_code:
            connection.execute(
                text(
                    "UPDATE students SET attendance_code = :code WHERE id = :id"
                ),
                {"code": secrets.token_urlsafe(24), "id": student_id},
            )


initialize_database()

ADMIN_PASSWORD = os.getenv("ATTENDANCE_ADMIN_PASSWORD", "local-dev-only")
TOKEN_SECRET = os.getenv("ATTENDANCE_TOKEN_SECRET", secrets.token_urlsafe(48))
TOKEN_LIFETIME_SECONDS = 12 * 60 * 60
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(title="Student Attendance")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class StudentCreate(BaseModel):
    name: str
    roll_no: str


class StudentOut(BaseModel):
    id: int
    name: str
    roll_no: str
    attendance_code: str

    class Config:
        from_attributes = True


class AttendanceMark(BaseModel):
    student_id: int
    date: date_type
    present: bool


class ScanAttendance(BaseModel):
    attendance_code: str = Field(min_length=1)
    date: date_type = Field(default_factory=date_type.today)


class AdminLogin(BaseModel):
    password: str = Field(min_length=1)


def encode_token(payload: dict) -> str:
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    signature = hmac.new(
        TOKEN_SECRET.encode(), encoded_payload.encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{encoded_payload}.{encoded_signature}"


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Admin login required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        encoded_payload, provided_signature = credentials.credentials.split(".")
        expected_signature = hmac.new(
            TOKEN_SECRET.encode(), encoded_payload.encode(), hashlib.sha256
        ).digest()
        decoded_signature = base64.urlsafe_b64decode(
            provided_signature + "=" * (-len(provided_signature) % 4)
        )
        if not hmac.compare_digest(expected_signature, decoded_signature):
            raise ValueError("Invalid signature")

        payload = json.loads(
            base64.urlsafe_b64decode(
                encoded_payload + "=" * (-len(encoded_payload) % 4)
            )
        )
        if payload.get("exp", 0) < time.time():
            raise ValueError("Expired token")
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=401,
            detail="Admin session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/auth/login")
def login(credentials: AdminLogin):
    if not hmac.compare_digest(credentials.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Incorrect admin password")
    token = encode_token({"exp": int(time.time()) + TOKEN_LIFETIME_SECONDS})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/students", response_model=StudentOut, status_code=201)
def add_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    existing = (
        db.query(models.Student)
        .filter(models.Student.roll_no == student.roll_no)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Roll number already exists")

    new_student = models.Student(
        name=student.name,
        roll_no=student.roll_no,
        attendance_code=secrets.token_urlsafe(24),
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


@app.get("/students", response_model=list[StudentOut])
def list_students(
    db: Session = Depends(get_db), _admin: None = Depends(require_admin)
):
    return db.query(models.Student).order_by(models.Student.name).all()


@app.post("/attendance")
def mark_attendance(
    record: AttendanceMark,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    student = (
        db.query(models.Student)
        .filter(models.Student.id == record.student_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    existing = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.student_id == record.student_id,
            models.Attendance.date == record.date,
        )
        .first()
    )
    if existing:
        existing.present = record.present
    else:
        db.add(
            models.Attendance(
                student_id=record.student_id,
                date=record.date,
                present=record.present,
            )
        )
    db.commit()
    return {"message": "Attendance updated" if existing else "Attendance marked"}


@app.post("/attendance/scan")
def mark_attendance_by_code(
    record: ScanAttendance,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    student = (
        db.query(models.Student)
        .filter(models.Student.attendance_code == record.attendance_code.strip())
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Attendance code not recognized")

    existing = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.student_id == student.id,
            models.Attendance.date == record.date,
        )
        .first()
    )
    if existing and existing.present:
        return {
            "message": "Attendance already marked",
            "name": student.name,
            "roll_no": student.roll_no,
            "date": record.date,
        }

    if existing:
        existing.present = True
    else:
        db.add(
            models.Attendance(
                student_id=student.id,
                date=record.date,
                present=True,
            )
        )
    db.commit()
    return {
        "message": "Attendance marked",
        "name": student.name,
        "roll_no": student.roll_no,
        "date": record.date,
    }


@app.get("/attendance/{for_date}")
def get_attendance_by_date(
    for_date: date_type,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin),
):
    records = (
        db.query(models.Attendance)
        .filter(models.Attendance.date == for_date)
        .all()
    )
    return [
        {
            "student_id": record.student_id,
            "name": record.student.name,
            "roll_no": record.student.roll_no,
            "present": record.present,
        }
        for record in records
    ]


@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
