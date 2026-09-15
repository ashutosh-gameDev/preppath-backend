from fastapi import APIRouter

from app.api.v1.endpoints import (
    attempts,
    auth,
    courses,
    dev_auth,
    enrollments,
    exams,
    leaderboard,
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
    courses as admin_courses,
    dashboard as admin_dashboard,
    exams as admin_exams,
    notifications as admin_notifications,
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
api_router.include_router(exams.router)
api_router.include_router(practice.router)
api_router.include_router(tests.router)
api_router.include_router(pyq.router)
api_router.include_router(attempts.router)
api_router.include_router(statistics.router)
api_router.include_router(leaderboard.router)
api_router.include_router(profile.router)
api_router.include_router(notifications.router)
api_router.include_router(tools.router)
api_router.include_router(premium.router)
api_router.include_router(dev_auth.router)  # 404s unless ENVIRONMENT=development

# Admin-only
api_router.include_router(admin_dashboard.router)
api_router.include_router(admin_courses.router)
api_router.include_router(admin_questions.router)
api_router.include_router(admin_tests.router)
api_router.include_router(admin_exams.router)
api_router.include_router(admin_notifications.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_settings.router)
api_router.include_router(admin_team.router)
