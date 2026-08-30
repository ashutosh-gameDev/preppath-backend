"""
Realistic demo/seed data for local development.

Everything created here is clearly tagged as seed content so it can be found
and removed later:
  * Question.source == SEED_SOURCE
  * Test.title is prefixed with SEED_PREFIX
  * seeded student emails end with SEED_EMAIL_DOMAIN

Run with:  python -m app.seed.seed_data
Remove with:  python scripts/clear_seed_data.py

This script is idempotent - it clears any previously seeded rows (matching
the tags above) before inserting fresh ones, so it's safe to re-run.
"""
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.admin import Report  # noqa
from app.models.attempt import Attempt
from app.models.course import Course, Subject, Topic
from app.models.enums import (
    AchievementCriteria,
    ContentStatus,
    ExamEventType,
    TestAttemptStatus,
    TestType,
    UserRole,
    XPReason,
)
from app.models.enrollment import CourseEnrollment
from app.models.exam import Exam, ExamEvent, UserExamFollow
from app.models.gamification import Achievement, UserAchievement, XPTransaction
from app.models.question import Question, Tag
from app.models.test import Test, TestAttempt, TestQuestion, TestSection
from app.models.user import Profile, User
from app.schemas.test import AutoSelectRule, TestCreate
from app.seed.question_bank import (
    BANKING_AWARENESS,
    ENGLISH,
    GENERAL_AWARENESS,
    REASONING,
    generate_quant_questions,
)
from app.services import test_service
from app.services.xp_service import xp_to_level

SEED_SOURCE = "Seed Demo Data"
SEED_PREFIX = "[Seed] "
SEED_EMAIL_DOMAIN = "@example.com"

RNG = random.Random(7)


def _slug(text: str) -> str:
    return text.lower().replace(" ", "-").replace("&", "and").replace("--", "-")


def clear_seed_data(db) -> None:
    print("Clearing any previously seeded data...")
    seed_users = db.execute(select(User).where(User.email.like(f"%{SEED_EMAIL_DOMAIN}"))).scalars().all()
    seed_user_ids = [u.id for u in seed_users]
    if seed_user_ids:
        db.query(Attempt).filter(Attempt.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(TestAttempt).filter(TestAttempt.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(XPTransaction).filter(XPTransaction.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(UserAchievement).filter(UserAchievement.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(UserExamFollow).filter(UserExamFollow.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(CourseEnrollment).filter(CourseEnrollment.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(Profile).filter(Profile.user_id.in_(seed_user_ids)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(seed_user_ids)).delete(synchronize_session=False)

    seed_tests = db.execute(select(Test).where(Test.title.like(f"{SEED_PREFIX}%"))).scalars().all()
    for t in seed_tests:
        db.query(TestAttempt).filter(TestAttempt.test_id == t.id).delete(synchronize_session=False)
        db.query(TestQuestion).filter(TestQuestion.test_id == t.id).delete(synchronize_session=False)
        db.query(TestSection).filter(TestSection.test_id == t.id).delete(synchronize_session=False)
        db.delete(t)

    db.query(Question).filter(Question.source == SEED_SOURCE).delete(synchronize_session=False)
    db.query(Achievement).delete(synchronize_session=False)

    for exam in db.execute(select(Exam)).scalars().all():
        db.query(ExamEvent).filter(ExamEvent.exam_id == exam.id).delete(synchronize_session=False)
        db.delete(exam)

    for course in db.execute(select(Course)).scalars().all():
        db.delete(course)

    db.flush()
    db.commit()


def seed_courses_and_taxonomy(db) -> dict:
    """Returns a lookup: {course_slug: {"course": Course, "subjects": {name: Subject}, "topics": {(subject_name, topic_name): Topic}}}"""
    structure = {
        "SSC CGL": {
            "description": "Staff Selection Commission - Combined Graduate Level exam preparation.",
            "subjects": {
                "Quantitative Aptitude": ["Percentage", "Profit and Loss", "Simple and Compound Interest", "Number System", "Averages", "Ratio and Proportion"],
                "Reasoning": ["Analogy", "Coding-Decoding", "Blood Relations", "Series", "Puzzles", "Syllogism"],
                "English Language": ["Grammar", "Vocabulary", "Reading Comprehension", "Cloze Test"],
                "General Awareness": ["Indian Polity", "Modern History", "Geography", "Economics", "Static GK", "Science"],
            },
        },
        "Bank PO": {
            "description": "Bank Probationary Officer exam preparation (Prelims + Mains).",
            "subjects": {
                "Quantitative Aptitude": ["Percentage", "Number System", "Averages", "Ratio and Proportion"],
                "Reasoning Ability": ["Puzzles", "Seating Arrangement", "Syllogism", "Inequalities"],
                "English Language": ["Grammar", "Vocabulary", "Reading Comprehension"],
                "Banking Awareness": ["Banking Basics", "Monetary Policy", "Financial Institutions", "Current Affairs"],
            },
        },
    }

    result = {}
    for order, (course_name, spec) in enumerate(structure.items()):
        course = Course(
            name=course_name,
            slug=_slug(course_name),
            description=spec["description"] + " (Demo seed course for local development.)",
            icon="graduation-cap",
            is_published=True,
        )
        db.add(course)
        db.flush()

        subjects = {}
        topics = {}
        for s_order, (subject_name, topic_names) in enumerate(spec["subjects"].items()):
            subject = Subject(
                course_id=course.id, name=subject_name, slug=_slug(subject_name), order_index=s_order, is_published=True
            )
            db.add(subject)
            db.flush()
            subjects[subject_name] = subject
            for t_order, topic_name in enumerate(topic_names):
                topic = Topic(
                    subject_id=subject.id, name=topic_name, slug=_slug(topic_name), order_index=t_order, is_published=True
                )
                db.add(topic)
                db.flush()
                topics[(subject_name, topic_name)] = topic

        result[course.slug] = {"course": course, "subjects": subjects, "topics": topics}
    db.flush()
    return result


def seed_questions(db, taxonomy: dict, admin_id: uuid.UUID) -> dict:
    """Populate Question rows for every topic. Returns {(course_slug, subject_name, topic_name): [Question,...]}"""
    quant_bank = generate_quant_questions()
    topic_pools = {
        "Reasoning": REASONING,
        "Reasoning Ability": REASONING,
        "English Language": ENGLISH,
        "General Awareness": GENERAL_AWARENESS,
        "Banking Awareness": BANKING_AWARENESS,
    }

    questions_by_scope: dict = {}
    years = [2023, 2024, 2025]

    for course_slug, data in taxonomy.items():
        course = data["course"]
        for subject_name, subject in data["subjects"].items():
            pool = quant_bank if subject_name == "Quantitative Aptitude" else topic_pools.get(subject_name, {})
            for (s_name, t_name), topic in data["topics"].items():
                if s_name != subject_name:
                    continue
                entries = pool.get(t_name, [])
                scope_key = (course_slug, subject_name, t_name)
                questions_by_scope[scope_key] = []
                for i, (text, options, correct_letter, explanation, difficulty) in enumerate(entries):
                    # Distribute question_type: mostly practice, some tagged
                    # as PYQ (with a year) and a couple reserved for mocks.
                    if i == 0:
                        q_type, year = "pyq", RNG.choice(years)
                    elif i == 1:
                        q_type, year = "pyq", RNG.choice(years)
                    else:
                        q_type, year = "practice", None

                    question = Question(
                        course_id=course.id,
                        subject_id=subject.id,
                        topic_id=topic.id,
                        question_text=text,
                        option_a=options[0],
                        option_b=options[1],
                        option_c=options[2],
                        option_d=options[3],
                        correct_option=correct_letter,
                        explanation=explanation,
                        difficulty=difficulty,
                        question_type=q_type,
                        year=year,
                        source=SEED_SOURCE,
                        status=ContentStatus.PUBLISHED,
                        created_by=admin_id,
                    )
                    db.add(question)
                    db.flush()
                    questions_by_scope[scope_key].append(question)
    db.flush()
    total = sum(len(v) for v in questions_by_scope.values())
    print(f"Seeded {total} questions across {len(questions_by_scope)} topics.")
    return questions_by_scope


def seed_exams(db, taxonomy: dict) -> dict:
    today = date.today()
    exams = {}

    ssc = Exam(
        course_id=taxonomy["ssc-cgl"]["course"].id,
        name="SSC CGL 2026",
        slug="ssc-cgl-2026",
        description="Staff Selection Commission Combined Graduate Level 2026 examination.",
        conducting_body="Staff Selection Commission",
        is_published=True,
    )
    bank = Exam(
        course_id=taxonomy["bank-po"]["course"].id,
        name="Bank PO 2026",
        slug="bank-po-2026",
        description="Probationary Officer recruitment exam 2026.",
        conducting_body="IBPS",
        is_published=True,
    )
    db.add_all([ssc, bank])
    db.flush()
    exams["ssc-cgl"] = ssc
    exams["bank-po"] = bank

    event_specs = {
        ssc.id: [
            (ExamEventType.APPLICATION_START, "Application Window Opens", today - timedelta(days=40)),
            (ExamEventType.APPLICATION_END, "Application Deadline", today - timedelta(days=10)),
            (ExamEventType.ADMIT_CARD, "Admit Card Release", today + timedelta(days=14)),
            (ExamEventType.EXAM_DATE, "Tier 1 Exam Date", today + timedelta(days=28)),
            (ExamEventType.RESULT, "Tier 1 Result", today + timedelta(days=70)),
        ],
        bank.id: [
            (ExamEventType.APPLICATION_START, "Application Window Opens", today - timedelta(days=20)),
            (ExamEventType.APPLICATION_END, "Application Deadline", today + timedelta(days=5)),
            (ExamEventType.ADMIT_CARD, "Admit Card Release", today + timedelta(days=35)),
            (ExamEventType.EXAM_DATE, "Prelims Exam Date", today + timedelta(days=45)),
        ],
    }
    for exam_id, events in event_specs.items():
        for event_type, title, event_date in events:
            db.add(
                ExamEvent(
                    exam_id=exam_id,
                    event_type=event_type,
                    title=title,
                    description=f"{title} - official notification will be posted on the commission's website.",
                    event_date=event_date,
                    external_link="https://example.gov.in/notifications",
                    is_published=True,
                )
            )
    db.flush()
    return exams


def seed_achievements(db) -> list[Achievement]:
    specs = [
        ("first_test", "First Test", "Complete your first mock test or PYQ paper.", "flag", AchievementCriteria.FIRST_TEST, 1, 20),
        ("hundred_questions", "100 Questions", "Attempt 100 questions.", "target", AchievementCriteria.QUESTIONS_ATTEMPTED, 100, 50),
        ("thousand_questions", "1,000 Questions", "Attempt 1,000 questions.", "trophy", AchievementCriteria.QUESTIONS_ATTEMPTED, 1000, 200),
        ("ninety_accuracy", "90% Accuracy", "Reach 90% accuracy over at least 20 answered questions.", "star", AchievementCriteria.ACCURACY_PCT, 90, 100),
        ("week_streak", "7 Day Streak", "Practice 7 days in a row.", "flame", AchievementCriteria.STREAK_DAYS, 7, 50),
        ("hundred_day_streak", "100 Day Streak", "Practice 100 days in a row.", "flame", AchievementCriteria.STREAK_DAYS, 100, 500),
        ("top_100", "Top 100", "Reach the top 100 on the global leaderboard.", "medal", AchievementCriteria.GLOBAL_RANK_TOP_N, 100, 150),
        ("pyq_master", "PYQ Master", "Complete 10 PYQ papers.", "book", AchievementCriteria.PYQ_COMPLETED, 10, 150),
    ]
    achievements = []
    for code, name, desc, icon, criteria_type, criteria_value, xp in specs:
        a = Achievement(code=code, name=name, description=desc, icon=icon, criteria_type=criteria_type, criteria_value=criteria_value, xp_reward=xp)
        db.add(a)
        achievements.append(a)
    db.flush()
    return achievements


def seed_tests(db, taxonomy: dict, exams: dict, questions_by_scope: dict, admin_id: uuid.UUID) -> None:
    for course_slug, exam_key in [("ssc-cgl", "ssc-cgl"), ("bank-po", "bank-po")]:
        data = taxonomy[course_slug]
        course = data["course"]
        exam = exams[exam_key]

        # Mock tests: one auto-built full-length test + one shorter subject test.
        rules = []
        for subject_name, subject in data["subjects"].items():
            available = sum(
                len(v) for k, v in questions_by_scope.items() if k[0] == course_slug and k[1] == subject_name
            )
            count = min(8, available)
            if count == 0:
                continue
            rules.append(
                AutoSelectRule(section_name=subject_name, subject_id=subject.id, count=count, marks=1, negative_marks=0.25)
            )
        if rules:
            payload = TestCreate(
                title=f"{SEED_PREFIX}{course.name} Full Mock Test 1",
                test_type=TestType.MOCK,
                course_id=course.id,
                exam_id=exam.id,
                duration_minutes=45,
                negative_marking=0.25,
                instructions="Attempt all questions. Each wrong answer deducts 0.25 marks.",
                status=ContentStatus.PUBLISHED,
                auto_rules=rules,
            )
            test_service.build_test(db, payload, admin_id)

        # PYQ papers: 2 years x 1-2 shifts, pulling from question_type='pyq' pool.
        for year in [2024, 2025]:
            pyq_questions = [
                q
                for scope, qs in questions_by_scope.items()
                if scope[0] == course_slug
                for q in qs
                if q.question_type == "pyq" and q.year == year
            ]
            if not pyq_questions:
                continue
            for shift in ["Shift 1", "Shift 2"]:
                subset = pyq_questions[: max(5, len(pyq_questions) // 2)] if shift == "Shift 1" else pyq_questions[len(pyq_questions) // 2 :]
                if not subset:
                    continue
                from app.schemas.test import TestQuestionIn

                payload = TestCreate(
                    title=f"{SEED_PREFIX}{course.name} PYQ {year} Tier 1 {shift}",
                    test_type=TestType.PYQ,
                    course_id=course.id,
                    exam_id=exam.id,
                    pyq_year=year,
                    pyq_paper_label=f"Tier 1 {shift}",
                    duration_minutes=30,
                    negative_marking=0.25,
                    status=ContentStatus.PUBLISHED,
                    questions=[TestQuestionIn(question_id=q.id, marks=1, negative_marks=0.25) for q in subset],
                )
                test_service.build_test(db, payload, admin_id)
    db.flush()
    print("Seeded mock tests and PYQ papers.")


STUDENT_PROFILES = [
    # (name, overall_skill 0-1, improving_subject_boost)
    ("Aarav Sharma", 0.85, None),
    ("Diya Patel", 0.55, "Economics"),
    ("Vihaan Kumar", 0.70, None),
    ("Ananya Singh", 0.40, "Reasoning"),
    ("Arjun Reddy", 0.90, None),
    ("Ishita Gupta", 0.60, "Geography"),
    ("Kabir Khan", 0.35, None),
    ("Myra Joshi", 0.75, "Banking Awareness"),
    ("Reyansh Nair", 0.50, None),
    ("Saanvi Iyer", 0.80, None),
    ("Vivaan Mehta", 0.45, "English Language"),
    ("Aadhya Rao", 0.65, None),
]


def seed_users_and_attempts(db, taxonomy: dict, exams: dict, questions_by_scope: dict) -> None:
    all_questions = [q for qs in questions_by_scope.values() for q in qs]

    for i, (name, skill, boost_subject) in enumerate(STUDENT_PROFILES):
        email = f"{name.lower().replace(' ', '.')}{SEED_EMAIL_DOMAIN}"
        user = User(
            id=uuid.uuid4(),
            email=email,
            full_name=name,
            role=UserRole.STUDENT,
            is_active=True,
            last_active_at=datetime.now(timezone.utc) - timedelta(hours=RNG.randint(0, 48)),
        )
        db.add(user)
        db.flush()
        profile = Profile(user_id=user.id, daily_goal_questions=RNG.choice([10, 15, 20, 25]))
        db.add(profile)
        db.flush()

        # Follow 1-2 exams.
        for exam in RNG.sample(list(exams.values()), k=RNG.choice([1, 2])):
            db.add(UserExamFollow(user_id=user.id, exam_id=exam.id))

        # Enroll in 1-2 courses ("My Courses") - independent of exam-following,
        # mirrors the real onboarding flow (pick a course, add more later).
        courses = [data["course"] for data in taxonomy.values()]
        for course in RNG.sample(courses, k=RNG.choice([1, len(courses)])):
            db.add(CourseEnrollment(user_id=user.id, course_id=course.id))

        _simulate_history(db, user, profile, all_questions, skill, boost_subject)
        db.flush()
        print(f"  seeded {name} ({email}) - {profile.questions_attempted} attempts, {profile.xp_total} XP, streak {profile.current_streak}")

    db.flush()


def _simulate_history(db, user: User, profile: Profile, all_questions: list[Question], skill: float, boost_subject: str | None) -> None:
    """Generate ~60 days of backdated practice history with a plausible
    accuracy curve per subject (optionally improving in `boost_subject` over
    the most recent 30 days, to make the Improvement panel meaningful)."""
    now = datetime.now(timezone.utc)
    days_back = 60
    streak_days = sorted(RNG.sample(range(days_back), k=int(days_back * RNG.uniform(0.35, 0.75))))

    xp_total = 0
    correct_total = 0
    attempted_total = 0
    tests_completed = 0
    longest_streak = 0
    current_run = 0
    last_day_offset = None

    for day_offset in streak_days:
        attempt_date = now - timedelta(days=day_offset)
        n_questions = RNG.randint(3, 15)
        sample = RNG.sample(all_questions, k=min(n_questions, len(all_questions)))

        for q in sample:
            subject = db.get(Subject, q.subject_id)
            subject_boost = 0.0
            if boost_subject and subject and subject.name == boost_subject and day_offset < 30:
                subject_boost = 0.25  # improved in the most recent period

            p_correct = min(0.97, max(0.15, skill + subject_boost + RNG.uniform(-0.1, 0.1)))
            is_correct = RNG.random() < p_correct
            selected = q.correct_option if is_correct else RNG.choice([o for o in "ABCD" if o != q.correct_option])
            time_taken = RNG.randint(15, 90)

            attempted_at = attempt_date - timedelta(minutes=RNG.randint(0, 600))
            db.add(
                Attempt(
                    user_id=user.id,
                    question_id=q.id,
                    course_id=q.course_id,
                    subject_id=q.subject_id,
                    topic_id=q.topic_id,
                    difficulty=q.difficulty,
                    question_type=q.question_type,
                    selected_option=selected,
                    is_correct=is_correct,
                    time_taken_seconds=time_taken,
                    attempted_at=attempted_at,
                )
            )
            attempted_total += 1
            if is_correct:
                correct_total += 1
                xp_amount = {"easy": 5, "medium": 10, "hard": 15}[q.difficulty]
                xp_total += xp_amount
                db.add(XPTransaction(user_id=user.id, amount=xp_amount, reason=XPReason.QUESTION_CORRECT, ref_type="question", ref_id=q.id, created_at=attempted_at))
            else:
                xp_total += 1
                db.add(XPTransaction(user_id=user.id, amount=1, reason=XPReason.QUESTION_ATTEMPT, ref_type="question", ref_id=q.id, created_at=attempted_at))

        # Streak bookkeeping (consecutive calendar days practiced).
        if last_day_offset is not None and last_day_offset - day_offset == 1:
            current_run += 1
        else:
            current_run = 1
        longest_streak = max(longest_streak, current_run)
        last_day_offset = day_offset

        # Occasionally simulate a completed mock/PYQ test on this day.
        if RNG.random() < 0.12:
            tests_completed += 1
            bonus = RNG.randint(20, 60)
            xp_total += bonus
            db.add(XPTransaction(user_id=user.id, amount=bonus, reason=XPReason.TEST_COMPLETED, created_at=attempt_date))

    profile.xp_total = xp_total
    profile.level = xp_to_level(xp_total)
    profile.questions_attempted = attempted_total
    profile.questions_correct = correct_total
    profile.tests_completed = tests_completed
    profile.pyqs_completed = max(0, tests_completed // 3)
    profile.current_streak = current_run if (last_day_offset is not None and last_day_offset <= 1) else 0
    profile.longest_streak = max(longest_streak, profile.current_streak)
    profile.last_activity_date = (now - timedelta(days=last_day_offset)).date() if last_day_offset is not None else None

    from app.services.achievements_service import check_and_award

    check_and_award(db, profile)


def seed_admin(db) -> User:
    admin = db.execute(select(User).where(User.email == "admin@example.com")).scalar_one_or_none()
    if admin is None:
        admin = User(id=uuid.uuid4(), email="admin@example.com", full_name="Platform Admin", role=UserRole.SUPER_ADMIN, is_active=True)
        db.add(admin)
        db.flush()
        db.add(Profile(user_id=admin.id))
        db.flush()
    return admin


def main() -> None:
    db = SessionLocal()
    try:
        clear_seed_data(db)
        admin = seed_admin(db)
        taxonomy = seed_courses_and_taxonomy(db)
        questions_by_scope = seed_questions(db, taxonomy, admin.id)
        exams = seed_exams(db, taxonomy)
        seed_achievements(db)
        seed_tests(db, taxonomy, exams, questions_by_scope, admin.id)
        print("Seeding student demo accounts and attempt history (this simulates ~60 days of activity per student)...")
        seed_users_and_attempts(db, taxonomy, exams, questions_by_scope)
        db.commit()
        print("\nSeed complete.")
        print("NOTE: seeded student accounts are demo-only (not real Supabase Auth users) and cannot log in directly.")
        print("To explore the dashboards as yourself: sign up via the student app, then run")
        print("  python scripts/attach_demo_history.py --email you@example.com")
        print("to copy one seeded student's history onto your account.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
