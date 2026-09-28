# Project Presentation Kit

## Abstract

This project implements a role-aware student assignment portal using a React client and a Python REST API. Students can register, inspect coursework, submit private files, and read teacher feedback. Teachers can create assignments, inspect submissions, download student work, and record marks. A relational database stores identities and workflow metadata while a separate storage adapter holds file bytes. The default local configuration uses SQLite and a private filesystem directory; environment-selected PostgreSQL and S3-compatible storage provide a cloud deployment path. Automated tests exercise key authorization, upload, idempotency, and grading rules.

## Problem and Proposed System

Email attachments and shared folders fragment submission history, make deadline status difficult to audit, and separate grades from the files they describe. The proposed portal centralizes assignments, versions, status, and feedback behind authenticated role-based workflows. It uses cloud-style managed interfaces so the database and file service can be moved independently from the API while preserving the same client experience.

## Objectives and Outcomes

- Implement teacher and student workflows with explicit server-side access rules.
- Keep large assignment files outside relational database rows.
- Validate deadlines, supported file extensions, file size, and grading bounds on the server.
- Demonstrate local-first development, cloud-compatible configuration, containers, automated tests, and CI.
- Document the boundaries between implemented services and optional cloud infrastructure.

## Existing and Proposed Systems

The existing email/drive approach depends on manual naming, access sharing, and independent feedback channels. The proposed portal gives each submission a database record linked to its assignment and student, generates an opaque private storage path, and presents feedback within the same authenticated workspace. It does not replace a full institutional LMS, enrollment system, or plagiarism platform.

## Implementation Summary

The React SPA calls FastAPI REST endpoints with an expiring bearer JWT. Passwords are hashed with Argon2. SQLAlchemy models users, courses, assignments, and submissions; assignment and student ownership are checked before data or files are returned. Uploads are stored through a local or S3-compatible adapter, and only metadata plus the opaque storage key enter SQL. Submission timestamps are server-generated UTC timestamps. Teacher grading validates the maximum mark and records written feedback.

## Results and Limitations

The local application can demonstrate registration, seeded teacher/student access, assignment publishing, submission uploads, private downloads, feedback, dashboard summaries, and API-level authorization. The included automated backend tests pass in the development environment. The starter does not provision a public cloud account, managed authentication, CDN, autoscaling, queue workers, malware scanner, or production monitoring. It also uses simple demo course access rather than institution-managed enrollment. Those limitations are stated explicitly so deployment claims match the code.

## Future Scope

Add managed identity verification, invitation-only teacher provisioning, course rosters, an admin role, Alembic migrations, token revocation, direct resumable object uploads, malware scanning, queues and notifications, audit trails, rubric grading, backup/restore exercises, operational metrics, and browser end-to-end tests.

## Resume Bullets

- Built a cloud-ready assignment and feedback portal with FastAPI, React, SQLAlchemy, JWT authentication, Argon2 password hashing, and explicit student/teacher authorization rules.
- Designed a metadata/object separation with PostgreSQL-compatible models and private local/S3 storage adapters, including deadline status, versioning, protected downloads, and idempotent uploads.
- Added automated API tests, Docker Compose development infrastructure, GitHub Actions CI, and documented mappings to managed database, storage, and container services.

## Two-Line Project Description

Designed and implemented a role-based coursework portal for assignment publishing, private submissions, version tracking, and teacher feedback. Demonstrates cloud-ready REST architecture with a PostgreSQL-compatible data layer, private object storage adapter, container workflow, and automated authorization tests.

## LinkedIn / GitHub Description

Fieldnote Learning is a cloud-ready student assignment and feedback portal built to explore practical cloud application design. The project separates relational workflow metadata from private submission objects, applies server-side JWT role checks, and supports local development plus PostgreSQL/S3-compatible deployment configuration. It includes React dashboards, a FastAPI API, private file delivery, grading workflows, pytest coverage, Docker Compose, and GitHub Actions. Cloud provider resources are documented as deployment targets and are not claimed as provisioned by the local demo.

## Technical Skills Demonstrated

Python, FastAPI, REST API design, React, JavaScript, SQLAlchemy, SQLite, PostgreSQL, object storage, AWS S3 concepts, JWT, Argon2, RBAC, secure upload handling, Docker, Docker Compose, GitHub Actions, pytest, environment configuration, cloud architecture documentation.

## Interview Questions and Answers

1. **Explain your project.**

   I built a student assignment portal with separate student and teacher workflows. Teachers publish assignments and grade submissions; students submit versioned files and receive feedback. The React frontend talks to a FastAPI service, which enforces the roles and ownership rules. SQL stores metadata while files are private objects. I can run it locally with SQLite and local storage, or configure PostgreSQL and S3-compatible storage for a cloud deployment.

2. **Why did you separate the database from object storage?**

   Assignment records, deadlines, user IDs, grades, and feedback are structured and need relational queries, so they belong in SQL. File contents can be large and are better stored as objects. The database stores an opaque storage key and file metadata, not the binary. That keeps backups, queries, and storage scaling more appropriate to each data type.

3. **How does your authorization work?**

   The API verifies a signed, expiring JWT and loads the user from the database. Registration always creates a student. Teacher operations check the role and confirm that the teacher owns the assignment or course. Students can only fetch their own submission rows and downloads. I return not-found for another student’s file to avoid disclosing its existence.

4. **How do you protect uploaded files?**

   The server checks the authenticated role, assignment policy, deadline setting, extension allowlist, configured size limit, and PDF signature. It generates a unique object path instead of trusting the submitted path. Objects are private; downloads pass through an API ownership check. A production system should add malware scanning and stronger content inspection.

5. **How do deadlines and late work behave?**

   The server records UTC time rather than trusting a browser clock. It compares that timestamp with the assignment deadline and assigns `SUBMITTED` or `LATE`. An environment setting can reject late files instead. I normalize timezone-aware request deadlines to UTC and display those timestamps in the browser’s local timezone.

6. **What makes your upload endpoint retry-safe?**

   The client sends an idempotency key with an upload. The API scopes that key to the student and assignment and returns the original submission if the same request is retried, instead of creating another version. This helps after a timeout where the client does not know whether the first request completed.

7. **How would you scale this for a deadline surge?**

   I would run multiple stateless API instances behind a load balancer, use managed PostgreSQL with connection pooling, and move uploads directly to object storage using short-lived signed URLs. A queue can handle malware scans and notifications asynchronously. Static assets can use a CDN, and autoscaling plus rate limits can absorb peaks. Those cloud resources are the documented next deployment step, not configured in the local starter.

8. **What happens when storage or the database is unavailable?**

   A file read or write failure returns a service-unavailable response rather than a success confirmation. The UI surfaces that message and the client can retry with the same idempotency key. Database failures must be logged and monitored without exposing connection details. A production design would add request correlation, alerts, backups, and a durable outbox/queue for follow-on work.

9. **Which parts are actually cloud-ready, and what is still future work?**

   The application can use PostgreSQL through SQLAlchemy and a private S3-compatible storage adapter through environment settings. The API can be placed in a container platform and the frontend served from static hosting. The starter does not create cloud resources, use a managed identity provider, deploy a CDN, or configure autoscaling; those are documented provider mappings and deployment tasks.

10. **What would you improve before production?**

   I would use a managed identity provider or secure HttpOnly sessions, add token revocation, course enrollment and admin provisioning, schema migrations, malware scanning, rate limiting, audit records, resumable uploads, observability, and end-to-end tests. I would also run backup/restore drills and verify the S3 bucket and database policies in a staging environment.