"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: auto-generated

"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE users (
	id UUID NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255), 
	avatar_url VARCHAR(1000), 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	last_active_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)""")
    op.execute("""CREATE UNIQUE INDEX ix_users_email ON users (email)""")
    op.execute("""CREATE TABLE courses (
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(255) NOT NULL, 
	description TEXT, 
	icon VARCHAR(50), 
	is_published BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)""")
    op.execute("""CREATE UNIQUE INDEX ix_courses_slug ON courses (slug)""")
    op.execute("""CREATE TABLE tags (
	name VARCHAR(100) NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)""")
    op.execute("""CREATE TABLE achievements (
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	icon VARCHAR(50), 
	criteria_type VARCHAR(30) NOT NULL, 
	criteria_value INTEGER NOT NULL, 
	xp_reward INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
)""")
    op.execute("""CREATE TABLE platform_settings (
	key VARCHAR(100) NOT NULL, 
	value JSON NOT NULL, 
	description VARCHAR(500), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (key)
)""")
    op.execute("""CREATE TABLE profiles (
	user_id UUID NOT NULL, 
	xp_total INTEGER NOT NULL, 
	level INTEGER NOT NULL, 
	current_streak INTEGER NOT NULL, 
	longest_streak INTEGER NOT NULL, 
	last_activity_date DATE, 
	daily_goal_questions INTEGER NOT NULL, 
	questions_attempted INTEGER NOT NULL, 
	questions_correct INTEGER NOT NULL, 
	tests_completed INTEGER NOT NULL, 
	pyqs_completed INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE subjects (
	course_id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(255) NOT NULL, 
	order_index INTEGER NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_subject_course_slug UNIQUE (course_id, slug), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE exams (
	course_id UUID, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(255) NOT NULL, 
	description TEXT, 
	conducting_body VARCHAR(255), 
	is_published BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL
)""")
    op.execute("""CREATE UNIQUE INDEX ix_exams_slug ON exams (slug)""")
    op.execute("""CREATE TABLE xp_transactions (
	user_id UUID NOT NULL, 
	amount INTEGER NOT NULL, 
	reason VARCHAR(30) NOT NULL, 
	ref_type VARCHAR(30), 
	ref_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE INDEX ix_xp_transactions_created_at ON xp_transactions (created_at)""")
    op.execute("""CREATE INDEX ix_xp_transactions_user_id ON xp_transactions (user_id)""")
    op.execute("""CREATE TABLE user_achievements (
	user_id UUID NOT NULL, 
	achievement_id UUID NOT NULL, 
	earned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_achievement UNIQUE (user_id, achievement_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(achievement_id) REFERENCES achievements (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE INDEX ix_user_achievements_user_id ON user_achievements (user_id)""")
    op.execute("""CREATE TABLE notifications (
	user_id UUID NOT NULL, 
	type VARCHAR(30) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	ref_type VARCHAR(30), 
	ref_id UUID, 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE INDEX ix_notifications_created_at ON notifications (created_at)""")
    op.execute("""CREATE INDEX ix_notifications_user_id ON notifications (user_id)""")
    op.execute("""CREATE TABLE admin_activity_logs (
	admin_user_id UUID, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id UUID, 
	extra JSON, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(admin_user_id) REFERENCES users (id) ON DELETE SET NULL
)""")
    op.execute("""CREATE TABLE topics (
	subject_id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(255) NOT NULL, 
	order_index INTEGER NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_topic_subject_slug UNIQUE (subject_id, slug), 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE exam_events (
	exam_id UUID NOT NULL, 
	event_type VARCHAR(30) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	event_date DATE NOT NULL, 
	external_link VARCHAR(1000), 
	is_published BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE user_exam_follows (
	user_id UUID NOT NULL, 
	exam_id UUID NOT NULL, 
	notifications_enabled BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_exam_follow UNIQUE (user_id, exam_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE tests (
	title VARCHAR(255) NOT NULL, 
	test_type VARCHAR(10) NOT NULL, 
	course_id UUID, 
	exam_id UUID, 
	pyq_year INTEGER, 
	pyq_paper_label VARCHAR(255), 
	duration_minutes INTEGER NOT NULL, 
	total_questions INTEGER NOT NULL, 
	total_marks FLOAT NOT NULL, 
	marks_per_question FLOAT NOT NULL, 
	negative_marking FLOAT NOT NULL, 
	difficulty VARCHAR(10), 
	instructions TEXT, 
	status VARCHAR(20) NOT NULL, 
	created_by UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL, 
	FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)""")
    op.execute("""CREATE INDEX ix_tests_status ON tests (status)""")
    op.execute("""CREATE INDEX ix_tests_test_type ON tests (test_type)""")
    op.execute("""CREATE INDEX ix_tests_exam_id ON tests (exam_id)""")
    op.execute("""CREATE INDEX ix_tests_pyq_year ON tests (pyq_year)""")
    op.execute("""CREATE TABLE questions (
	course_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	topic_id UUID, 
	exam_id UUID, 
	question_text TEXT NOT NULL, 
	image_url VARCHAR(1000), 
	option_a TEXT NOT NULL, 
	option_b TEXT NOT NULL, 
	option_c TEXT NOT NULL, 
	option_d TEXT NOT NULL, 
	correct_option VARCHAR(1) NOT NULL, 
	explanation TEXT, 
	difficulty VARCHAR(10) NOT NULL, 
	question_type VARCHAR(20) NOT NULL, 
	year INTEGER, 
	source VARCHAR(255), 
	status VARCHAR(20) NOT NULL, 
	created_by UUID, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL, 
	FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)""")
    op.execute("""CREATE INDEX ix_questions_status ON questions (status)""")
    op.execute("""CREATE INDEX ix_questions_question_type ON questions (question_type)""")
    op.execute("""CREATE TABLE test_sections (
	test_id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	order_index INTEGER NOT NULL, 
	num_questions INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(test_id) REFERENCES tests (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE test_attempts (
	user_id UUID NOT NULL, 
	test_id UUID NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE, 
	score FLOAT NOT NULL, 
	correct_count INTEGER NOT NULL, 
	incorrect_count INTEGER NOT NULL, 
	skipped_count INTEGER NOT NULL, 
	accuracy FLOAT NOT NULL, 
	time_taken_seconds INTEGER NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(test_id) REFERENCES tests (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE INDEX ix_test_attempts_test_id ON test_attempts (test_id)""")
    op.execute("""CREATE INDEX ix_test_attempts_user_id ON test_attempts (user_id)""")
    op.execute("""CREATE TABLE question_tags (
	question_id UUID NOT NULL, 
	tag_id UUID NOT NULL, 
	PRIMARY KEY (question_id, tag_id), 
	FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE test_questions (
	test_id UUID NOT NULL, 
	section_id UUID, 
	question_id UUID NOT NULL, 
	order_index INTEGER NOT NULL, 
	marks FLOAT NOT NULL, 
	negative_marks FLOAT NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(test_id) REFERENCES tests (id) ON DELETE CASCADE, 
	FOREIGN KEY(section_id) REFERENCES test_sections (id) ON DELETE SET NULL, 
	FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE TABLE attempts (
	user_id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	course_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	topic_id UUID, 
	test_attempt_id UUID, 
	difficulty VARCHAR(10) NOT NULL, 
	question_type VARCHAR(20) NOT NULL, 
	selected_option VARCHAR(1), 
	is_correct BOOLEAN, 
	time_taken_seconds INTEGER NOT NULL, 
	attempted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE, 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE, 
	FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL, 
	FOREIGN KEY(test_attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE
)""")
    op.execute("""CREATE INDEX ix_attempts_topic_id ON attempts (topic_id)""")
    op.execute("""CREATE INDEX ix_attempts_user_id ON attempts (user_id)""")
    op.execute("""CREATE INDEX ix_attempts_course_id ON attempts (course_id)""")
    op.execute("""CREATE INDEX ix_attempts_attempted_at ON attempts (attempted_at)""")
    op.execute("""CREATE INDEX ix_attempts_test_attempt_id ON attempts (test_attempt_id)""")
    op.execute("""CREATE INDEX ix_attempts_question_id ON attempts (question_id)""")
    op.execute("""CREATE INDEX ix_attempts_question_type ON attempts (question_type)""")
    op.execute("""CREATE INDEX ix_attempts_subject_id ON attempts (subject_id)""")
    op.execute("""CREATE TABLE reports (
	user_id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	reason VARCHAR(100) NOT NULL, 
	description TEXT, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	reviewed_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE, 
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
)""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS test_questions CASCADE;")
    op.execute("DROP TABLE IF EXISTS reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS question_tags CASCADE;")
    op.execute("DROP TABLE IF EXISTS attempts CASCADE;")
    op.execute("DROP TABLE IF EXISTS test_sections CASCADE;")
    op.execute("DROP TABLE IF EXISTS test_attempts CASCADE;")
    op.execute("DROP TABLE IF EXISTS questions CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_exam_follows CASCADE;")
    op.execute("DROP TABLE IF EXISTS topics CASCADE;")
    op.execute("DROP TABLE IF EXISTS tests CASCADE;")
    op.execute("DROP TABLE IF EXISTS exam_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS xp_transactions CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_achievements CASCADE;")
    op.execute("DROP TABLE IF EXISTS subjects CASCADE;")
    op.execute("DROP TABLE IF EXISTS profiles CASCADE;")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS exams CASCADE;")
    op.execute("DROP TABLE IF EXISTS admin_activity_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TABLE IF EXISTS tags CASCADE;")
    op.execute("DROP TABLE IF EXISTS platform_settings CASCADE;")
    op.execute("DROP TABLE IF EXISTS courses CASCADE;")
    op.execute("DROP TABLE IF EXISTS achievements CASCADE;")
