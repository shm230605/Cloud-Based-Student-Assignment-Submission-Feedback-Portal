import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import jwt
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    ALLOW_LATE_SUBMISSIONS,
    FRONTEND_ORIGINS,
    JWT_SECRET,
    MAX_UPLOAD_MB,
)
from app.database import Base, SessionLocal, engine, get_db
from app.models import Assignment, Course, Submission, User, utc_now
from app.schemas import (
    AssignmentInput,
    AssignmentView,
    DashboardView,
    GradeInput,
    LoginInput,
    RegisterInput,
    SubmissionView,
    TokenView,
    UserView,
)
from app.security import create_access_token, hash_password, verify_password
from app.storage import storage


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Classroom Cloud Portal API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def assignment_view(assignment: Assignment) -> dict:
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "course_name": assignment.course.name,
        "course_code": assignment.course.code,
        "title": assignment.title,
        "description": assignment.description,
        "deadline": as_utc(assignment.deadline),
        "max_marks": assignment.max_marks,
        "allowed_extensions": assignment.allowed_extensions.split(","),
        "allow_resubmission": assignment.allow_resubmission,
        "created_by": assignment.created_by,
    }


def submission_view(submission: Submission) -> dict:
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title,
        "student_id": submission.student_id,
        "student_name": submission.student.name,
        "student_email": submission.student.email,
        "file_name": submission.file_name,
        "file_size": submission.file_size,
        "submitted_at": as_utc(submission.submitted_at),
        "status": submission.status,
        "version": submission.version,
        "marks": submission.marks,
        "feedback": submission.feedback,
        "graded_at": as_utc(submission.graded_at) if submission.graded_at else None,
    }


def require_role(user: User, role: str) -> None:
    if user.role != role:
        raise HTTPException(status_code=403, detail=f"This action requires the {role} role.")


def owned_assignment(db: Session, assignment_id: int, teacher_id: int) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.created_by != teacher_id:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Your session is invalid or has expired.") from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return user


def seed_demo_data() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            return
        teacher_email = os.getenv("DEMO_TEACHER_EMAIL", "teacher@example.edu").lower()
        student_email = os.getenv("DEMO_STUDENT_EMAIL", "student@example.edu").lower()
        teacher_password = os.getenv("DEMO_TEACHER_PASSWORD")
        student_password = os.getenv("DEMO_STUDENT_PASSWORD")
        if not teacher_password or not student_password:
            return
        teacher = User(name="Morgan Lee", email=teacher_email, password_hash=hash_password(teacher_password), role="teacher")
        student = User(name="Alex Morgan", email=student_email, password_hash=hash_password(student_password), role="student")
        db.add_all([teacher, student])
        db.flush()
        course = Course(name="Cloud Systems Engineering", code="CSE 240", teacher_id=teacher.id)
        db.add(course)
        db.flush()
        db.add_all([
            Assignment(
                course_id=course.id,
                created_by=teacher.id,
                title="Cloud Architecture Brief",
                description="Map a secure, scalable cloud workflow and explain its storage and identity boundaries.",
                deadline=utc_now() + timedelta(days=7),
                max_marks=100,
                allowed_extensions=".pdf,.docx,.png,.jpg,.jpeg",
            ),
            Assignment(
                course_id=course.id,
                created_by=teacher.id,
                title="Resilient API Design",
                description="Submit a short design note describing retries, idempotency, and failure recovery.",
                deadline=utc_now() + timedelta(days=14),
                max_marks=50,
                allowed_extensions=".pdf,.docx",
            ),
        ])
        db.commit()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    seed_demo_data()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "classroom-cloud-portal"}


@app.post("/api/auth/register", response_model=TokenView, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterInput, db: Session = Depends(get_db)) -> dict:
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="student")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id, user.role), "user": user}


@app.post("/api/auth/login", response_model=TokenView)
def login(payload: LoginInput, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return {"access_token": create_access_token(user.id, user.role), "user": user}


@app.get("/api/auth/me", response_model=UserView)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user)) -> None:
    return None


@app.get("/api/courses")
def get_courses(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return [{"id": c.id, "name": c.name, "code": c.code} for c in db.scalars(select(Course).order_by(Course.code))]


@app.get("/api/assignments", response_model=list[AssignmentView])
def get_assignments(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    query = select(Assignment).order_by(Assignment.deadline)
    if user.role == "teacher":
        query = query.where(Assignment.created_by == user.id)
    return [assignment_view(row) for row in db.scalars(query).unique()]


@app.get("/api/assignments/{assignment_id}", response_model=AssignmentView)
def get_assignment(assignment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or (user.role == "teacher" and assignment.created_by != user.id):
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment_view(assignment)


@app.post("/api/assignments", response_model=AssignmentView, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_role(user, "teacher")
    course = db.get(Course, payload.course_id)
    if course is None or course.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found.")
    extensions = sorted({ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in payload.allowed_extensions})
    if not extensions or not set(extensions).issubset(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=422, detail="Allowed file types must be selected from PDF, DOCX, PNG, JPG, or JPEG.")
    assignment = Assignment(
        course_id=course.id,
        created_by=user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        deadline=as_utc(payload.deadline),
        max_marks=payload.max_marks,
        allowed_extensions=",".join(extensions),
        allow_resubmission=payload.allow_resubmission,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment_view(assignment)


@app.put("/api/assignments/{assignment_id}", response_model=AssignmentView)
def update_assignment(assignment_id: int, payload: AssignmentInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_role(user, "teacher")
    assignment = owned_assignment(db, assignment_id, user.id)
    course = db.get(Course, payload.course_id)
    if course is None or course.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found.")
    extensions = sorted({ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in payload.allowed_extensions})
    if not extensions or not set(extensions).issubset(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=422, detail="One or more file types are not supported.")
    for key, value in payload.model_dump(exclude={"allowed_extensions"}).items():
        setattr(assignment, key, as_utc(value) if key == "deadline" else value)
    assignment.allowed_extensions = ",".join(extensions)
    db.commit()
    db.refresh(assignment)
    return assignment_view(assignment)


@app.delete("/api/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    require_role(user, "teacher")
    assignment = owned_assignment(db, assignment_id, user.id)
    if db.scalar(select(Submission.id).where(Submission.assignment_id == assignment.id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Assignments with submissions cannot be deleted; archive them instead.")
    db.delete(assignment)
    db.commit()


@app.post("/api/assignments/{assignment_id}/submit", response_model=SubmissionView, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_role(user, "student")
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    prior_submissions = list(db.scalars(select(Submission).where(
        Submission.assignment_id == assignment_id,
        Submission.student_id == user.id,
    ).order_by(Submission.version.desc())))
    if prior_submissions and not assignment.allow_resubmission:
        raise HTTPException(status_code=409, detail="Resubmissions are disabled for this assignment.")
    now = utc_now()
    if now > as_utc(assignment.deadline) and not ALLOW_LATE_SUBMISSIONS:
        raise HTTPException(status_code=409, detail="The deadline has passed and late submissions are closed.")
    filename = Path((file.filename or "submission").replace("\\", "/")).name
    extension = Path(filename).suffix.lower()
    if extension not in assignment.allowed_extensions.split(","):
        raise HTTPException(status_code=415, detail="This file type is not allowed for the assignment.")
    content = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Files must be {MAX_UPLOAD_MB} MB or smaller.")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The file contents do not match a PDF document.")
    if idempotency_key:
        if len(idempotency_key) > 128:
            raise HTTPException(status_code=422, detail="Idempotency-Key must be 128 characters or fewer.")
        existing = db.scalar(select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == user.id,
            Submission.idempotency_key == idempotency_key,
        ))
        if existing:
            return submission_view(existing)
    version = (prior_submissions[0].version + 1) if prior_submissions else 1
    try:
        storage_path = storage.save(assignment_id, user.id, filename, content, file.content_type or "application/octet-stream")
    except Exception:
        raise HTTPException(status_code=503, detail="The file store is temporarily unavailable. Please retry.") from None
    row = Submission(
        assignment_id=assignment_id,
        student_id=user.id,
        file_name=filename,
        storage_path=storage_path,
        file_size=len(content),
        submitted_at=now,
        status="LATE" if now > as_utc(assignment.deadline) else "SUBMITTED",
        version=version,
        idempotency_key=idempotency_key,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return submission_view(row)


@app.get("/api/submissions/me", response_model=list[SubmissionView])
def get_my_submissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    require_role(user, "student")
    rows = db.scalars(select(Submission).where(Submission.student_id == user.id).order_by(Submission.submitted_at.desc())).unique()
    return [submission_view(row) for row in rows]


@app.get("/api/assignments/{assignment_id}/submissions", response_model=list[SubmissionView])
def get_assignment_submissions(assignment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    require_role(user, "teacher")
    owned_assignment(db, assignment_id, user.id)
    rows = db.scalars(select(Submission).where(Submission.assignment_id == assignment_id).order_by(Submission.submitted_at.desc())).unique()
    return [submission_view(row) for row in rows]


@app.get("/api/submissions/{submission_id}/download")
def download_submission(submission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StreamingResponse:
    row = db.get(Submission, submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if user.role == "student" and row.student_id != user.id:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if user.role == "teacher" and row.assignment.created_by != user.id:
        raise HTTPException(status_code=404, detail="Submission not found.")
    try:
        content = storage.read(row.storage_path)
    except Exception:
        raise HTTPException(status_code=503, detail="The file store is temporarily unavailable.") from None
    return StreamingResponse(
        BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.file_name)}"},
    )


@app.post("/api/submissions/{submission_id}/grade", response_model=SubmissionView)
def grade_submission(submission_id: int, payload: GradeInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_role(user, "teacher")
    row = db.get(Submission, submission_id)
    if row is None or row.assignment.created_by != user.id:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if payload.marks > row.assignment.max_marks:
        raise HTTPException(status_code=422, detail=f"Marks cannot exceed {row.assignment.max_marks}.")
    row.marks = payload.marks
    row.feedback = payload.feedback.strip()
    row.graded_at = utc_now()
    row.status = "GRADED"
    db.commit()
    db.refresh(row)
    return submission_view(row)


@app.get("/api/dashboard", response_model=DashboardView)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    assignments_query = select(Assignment).order_by(Assignment.deadline)
    if user.role == "teacher":
        assignments_query = assignments_query.where(Assignment.created_by == user.id)
    assignments = list(db.scalars(assignments_query).unique())
    assignment_ids = [item.id for item in assignments]
    if user.role == "teacher":
        submissions = list(db.scalars(select(Submission).where(Submission.assignment_id.in_(assignment_ids)).order_by(Submission.submitted_at.desc())).unique()) if assignment_ids else []
        students = db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
        return {
            "total_assignments": len(assignments),
            "pending_assignments": 0,
            "submitted_assignments": 0,
            "late_submissions": sum(row.status == "LATE" for row in submissions),
            "graded_submissions": sum(row.status == "GRADED" for row in submissions),
            "total_students": students,
            "total_submissions": len(submissions),
            "pending_reviews": sum(row.status != "GRADED" for row in submissions),
            "recent_submissions": [submission_view(row) for row in submissions[:6]],
            "assignments": [assignment_view(row) for row in assignments],
        }
    submissions = list(db.scalars(select(Submission).where(Submission.student_id == user.id).order_by(Submission.submitted_at.desc())).unique())
    latest = {}
    for row in submissions:
        latest.setdefault(row.assignment_id, row)
    return {
        "total_assignments": len(assignments),
        "pending_assignments": max(0, len(assignments) - len(latest)),
        "submitted_assignments": len(latest),
        "late_submissions": sum(row.status == "LATE" for row in latest.values()),
        "graded_submissions": sum(row.status == "GRADED" for row in latest.values()),
        "total_students": 0,
        "total_submissions": len(submissions),
        "pending_reviews": 0,
        "recent_submissions": [submission_view(row) for row in submissions[:6]],
        "assignments": [assignment_view(row) for row in assignments],
    }