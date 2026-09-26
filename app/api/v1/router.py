from fastapi import APIRouter

from app.api.v1.endpoints import (
    attempts,
    auth,
    bookmarks,
    courses,
    dev_auth,
    enrollments,
    jobs,
    leaderboard,
    mistakes,
    notes,
    notifications,
    practice,
    premium,
    profile,
    pyq,
    statistics,
    tests,
    tools,
    users,
)
from app.api.v1.endpoints.admin import (
    backup as admin_backup,
    courses as admin_courses,
    dashboard as admin_dashboard,
    job_postings as admin_job_postings,
    pyq_papers as admin_pyq_papers,
    questions as admin_questions,
    settings as admin_settings,
    team as admin_team,
    tests as admin_tests,
    users as admin_users,
)

api_router = APIRouter()

# Student-facing / shared
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(enrollments.router)
api_router.include_router(practice.router)
api_router.include_router(tests.router)
api_router.include_router(pyq.router)
api_router.include_router(attempts.router)
api_router.include_router(statistics.router)
api_router.include_router(leaderboard.router)
api_router.include_router(profile.router)
api_router.include_router(notifications.router)
api_router.include_router(jobs.router)
api_router.include_router(notes.router)
api_router.include_router(mistakes.router)
api_router.include_router(bookmarks.router)
api_router.include_router(tools.router)
api_router.include_router(premium.router)
api_router.include_router(dev_auth.router)  # 404s unless ENVIRONMENT=development

# Admin-only
api_router.include_router(admin_dashboard.router)
api_router.include_router(admin_backup.router)
api_router.include_router(admin_courses.router)
api_router.include_router(admin_questions.router)
api_router.include_router(admin_pyq_papers.router)
api_router.include_router(admin_job_postings.router)
api_router.include_router(admin_tests.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_settings.router)
api_router.include_router(admin_team.router)
