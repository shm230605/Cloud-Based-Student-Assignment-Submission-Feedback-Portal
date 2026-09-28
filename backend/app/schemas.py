from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserView(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenView(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class AssignmentInput(BaseModel):
    course_id: int
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(max_length=5000)
    deadline: datetime
    max_marks: int = Field(gt=0, le=1000)
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx", ".png", ".jpg", ".jpeg"])
    allow_resubmission: bool = True


class GradeInput(BaseModel):
    marks: float = Field(ge=0)
    feedback: str = Field(min_length=1, max_length=5000)


class CourseView(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class AssignmentView(BaseModel):
    id: int
    course_id: int
    course_name: str
    course_code: str
    title: str
    description: str
    deadline: datetime
    max_marks: int
    allowed_extensions: list[str]
    allow_resubmission: bool
    created_by: int


class SubmissionView(BaseModel):
    id: int
    assignment_id: int
    assignment_title: str
    student_id: int
    student_name: str
    student_email: str
    file_name: str
    file_size: int
    submitted_at: datetime
    status: str
    version: int
    marks: float | None
    feedback: str | None
    graded_at: datetime | None


class DashboardView(BaseModel):
    total_assignments: int
    pending_assignments: int
    submitted_assignments: int
    late_submissions: int
    graded_submissions: int
    total_students: int
    total_submissions: int
    pending_reviews: int
    recent_submissions: list[SubmissionView]
    assignments: list[AssignmentView]