# Testing and Proof Plan

## Automated Tests

Run from `backend/` with `python -m pytest -q`. The current automated suite runs against an isolated in-memory SQL database and fake private storage.

| Test | Automated coverage | Expected result |
|---|---|---|
| Student registration | Yes | Account is created with the student role regardless of a submitted role field |
| Teacher login | Yes, as test setup | Valid teacher credentials produce a signed token |
| Invalid login | Manual/API | `401`; no account or password details leaked |
| Student dashboard authorization | Manual/API | Student receives their dashboard; teacher-only actions are blocked |
| Teacher dashboard authorization | Manual/API | Teacher sees assignments they own and their review counts |
| Teacher creates assignment | Manual/API | Valid course-owned assignment returns `201` |
| Student views assignment | Manual/UI | Signed-in student sees available coursework |
| Valid PDF upload | Yes | Private object key and submission metadata are returned |
| Invalid extension | Yes | `415` and no submission metadata is created |
| Oversized file | Manual/API | `413` after setting a small `MAX_UPLOAD_MB` test limit |
| On-time submission | Manual/API | Status is `SUBMITTED` |
| Late submission | Manual/API | Status is `LATE` when accepted; `409` when late uploads are disabled |
| Resubmission/version increment | Manual/API | New row with incremented version when policy allows |
| Student views own submission | Yes, upload workflow | Own history is available to the authenticated student |
| Student cannot view another student's private submission | Yes | Download returns `404` to another student |
| Teacher views submissions | Manual/API | Owning teacher sees files for that assignment |
| Teacher grades a submission | Yes | Valid grade and feedback are stored, status becomes `GRADED` |
| Marks over maximum | Yes | Request returns `422` |
| Student views feedback | Manual/UI | Student sees saved marks and feedback on their submission |
| Unauthorized grading | Yes | Student receives `403` |
| File retrieval | Yes, authorization path | Owner/teacher receives bytes; unrelated student cannot retrieve them |
| Cloud-storage failure | Manual/API | Upload or download returns `503`; UI presents the service message |
| Database failure | Manual/operations | Health/readiness monitoring detects the unavailable dependency; do not expose connection details |
| Logout | Manual/UI | Browser session is removed and the sign-in view appears |
| Protected route after logout | Manual/API | Request without a token returns `401` |

The manual rows are test cases to execute during a project demonstration; they are not represented as already automated or passed. Add a test row for every newly introduced policy.

## Suggested Demo Sequence

1. Sign in as the configured teacher and show the assignment list and summary metrics.
2. Publish a coursework item with a deadline and max marks.
3. Open a separate browser profile, register or sign in as a student, and upload a sample PDF.
4. Show the new row in the student's submission history and the private object under the local storage folder.
5. Return to the teacher, download the work, grade it, and enter written feedback.
6. Return to the student and show the graded state, marks, and feedback.
7. Demonstrate a forbidden action (student attempts a teacher endpoint) and an invalid file type.
8. Show `backend/tests/` passing and the OpenAPI page at `/docs`.

## Screenshot Checklist

Store only synthetic/demo data. Do not capture tokens, `.env` contents, real student information, or cloud access keys.

| Filename | What it proves |
|---|---|
| `01-login.png` | Branded sign-in screen |
| `02-registration.png` | Student self-registration |
| `03-teacher-overview.png` | Teacher role dashboard and review metrics |
| `04-assignment-create.png` | Assignment title, course, deadline, and marks |
| `05-student-overview.png` | Student role view and pending counts |
| `06-coursework.png` | Student assignment list and due dates |
| `07-upload-confirmation.png` | Upload success and status |
| `08-private-object.png` | Local object path or cloud private bucket key |
| `09-submission-metadata.png` | SQL row fields without secrets |
| `10-teacher-review.png` | Teacher submission list and download control |
| `11-grade-feedback.png` | Saved teacher marks and written feedback |
| `12-student-feedback.png` | Student can see the returned grade |
| `13-access-denied.png` | API rejects an unauthorized role/owner |
| `14-openapi.png` | REST API documentation |
| `15-test-results.png` | Automated backend test run |
| `16-github-actions.png` | CI checks on the repository |
| `17-live-deployment.png` | Cloud resources and deployed application, after deployment |

## Development Milestones

| Milestone | Scope | Commit idea | Evidence |
|---|---|---|---|
| 1 | Architecture, repository, configuration | `Initialize assignment portal` | Repository tree and architecture diagram |
| 2 | JWT authentication, hashed passwords, role policy | `Add auth and role boundaries` | Sign-in and unauthorized request |
| 3 | Assignment and course API | `Implement assignment management` | Teacher publishes coursework |
| 4 | PostgreSQL-compatible data layer | `Add relational data models` | Tables and dashboard API |
| 5 | Private storage adapter | `Add private object storage` | Local object and protected download |
| 6 | Student submission/version/deadline flow | `Implement student submissions` | Confirmation and status |
| 7 | Teacher grading and feedback | `Add grading workflow` | Teacher/student grade screens |
| 8 | Tests, Docker, and CI | `Add tests and CI checks` | Passing tests and workflow |
| 9 | Cloud deployment and final report | `Document cloud deployment` | Deployment dashboard and README |