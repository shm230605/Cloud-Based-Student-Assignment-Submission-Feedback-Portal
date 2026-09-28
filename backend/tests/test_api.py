from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import Assignment, Course, User, utc_now
from app.security import hash_password


class MemoryStorage:
    files = {}

    def save(self, assignment_id, student_id, filename, content, content_type):
        key = f"{assignment_id}/{student_id}/{filename}"
        self.files[key] = content
        return key

    def read(self, key):
        return self.files[key]


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        teacher = User(name="Taylor Teacher", email="teacher@test.edu", password_hash=hash_password("Teacher-password-123"), role="teacher")
        student = User(name="Sam Student", email="student@test.edu", password_hash=hash_password("Student-password-123"), role="student")
        other = User(name="Robin Student", email="other@test.edu", password_hash=hash_password("Other-password-123"), role="student")
        db.add_all([teacher, student, other])
        db.flush()
        course = Course(name="Cloud Computing", code="CC101", teacher_id=teacher.id)
        db.add(course)
        db.flush()
        assignment = Assignment(
            course_id=course.id,
            created_by=teacher.id,
            title="Storage architecture",
            description="Explain object storage.",
            deadline=utc_now() + timedelta(days=2),
            max_marks=50,
            allowed_extensions=".pdf,.docx",
        )
        db.add(assignment)
        db.commit()
        assignment_id = assignment.id
        student_id = student.id

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main, "storage", MemoryStorage())
    main.app.dependency_overrides[get_db] = override_db
    with TestClient(main.app) as test_client:
        teacher_login = test_client.post("/api/auth/login", json={"email": "teacher@test.edu", "password": "Teacher-password-123"})
        student_login = test_client.post("/api/auth/login", json={"email": "student@test.edu", "password": "Student-password-123"})
        other_login = test_client.post("/api/auth/login", json={"email": "other@test.edu", "password": "Other-password-123"})
        yield {
            "http": test_client,
            "teacher": {"Authorization": f"Bearer {teacher_login.json()['access_token']}"},
            "student": {"Authorization": f"Bearer {student_login.json()['access_token']}"},
            "other": {"Authorization": f"Bearer {other_login.json()['access_token']}"},
            "assignment_id": assignment_id,
            "student_id": student_id,
        }
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_student_can_register_but_cannot_choose_teacher_role(client):
    response = client["http"].post("/api/auth/register", json={
        "name": "New Learner",
        "email": "new@test.edu",
        "password": "New-password-123",
        "role": "teacher",
    })
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "student"


def test_student_cannot_create_or_grade(client):
    create = client["http"].post("/api/assignments", headers=client["student"], json={
        "course_id": 1,
        "title": "Unauthorized assignment",
        "description": "This request must be blocked by role policy.",
        "deadline": (utc_now() + timedelta(days=1)).isoformat(),
        "max_marks": 10,
    })
    assert create.status_code == 403
    upload = client["http"].post(
        f"/api/assignments/{client['assignment_id']}/submit",
        headers=client["teacher"],
        files={"file": ("work.pdf", b"%PDF-test", "application/pdf")},
    )
    assert upload.status_code == 403


def test_submission_is_private_and_teacher_can_grade(client):
    upload = client["http"].post(
        f"/api/assignments/{client['assignment_id']}/submit",
        headers={**client["student"], "Idempotency-Key": "once-123"},
        files={"file": ("work.pdf", b"%PDF-test", "application/pdf")},
    )
    assert upload.status_code == 201
    submission_id = upload.json()["id"]
    forbidden = client["http"].get(f"/api/submissions/{submission_id}/download", headers=client["other"])
    assert forbidden.status_code == 404
    graded = client["http"].post(
        f"/api/submissions/{submission_id}/grade",
        headers=client["teacher"],
        json={"marks": 42, "feedback": "Clear diagrams and sound reasoning."},
    )
    assert graded.status_code == 200
    assert graded.json()["status"] == "GRADED"
    assert graded.json()["marks"] == 42


def test_idempotency_returns_original_submission(client):
    headers = {**client["student"], "Idempotency-Key": "same-request"}
    endpoint = f"/api/assignments/{client['assignment_id']}/submit"
    first = client["http"].post(endpoint, headers=headers, files={"file": ("work.pdf", b"%PDF-first", "application/pdf")})
    second = client["http"].post(endpoint, headers=headers, files={"file": ("work.pdf", b"%PDF-second", "application/pdf")})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_rejects_invalid_file_and_marks_above_maximum(client):
    endpoint = f"/api/assignments/{client['assignment_id']}/submit"
    bad_file = client["http"].post(endpoint, headers=client["student"], files={"file": ("notes.exe", b"bad", "application/octet-stream")})
    assert bad_file.status_code == 415
    good_file = client["http"].post(endpoint, headers=client["student"], files={"file": ("work.pdf", b"%PDF-test", "application/pdf")})
    too_many_marks = client["http"].post(
        f"/api/submissions/{good_file.json()['id']}/grade",
        headers=client["teacher"],
        json={"marks": 51, "feedback": "Out of range."},
    )
    assert too_many_marks.status_code == 422