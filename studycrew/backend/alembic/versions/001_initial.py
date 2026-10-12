"""Initial migration - create all tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('exam_date', sa.DateTime(), nullable=False),
        sa.Column('hours_per_day', sa.Float(), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create topics table
    op.create_table(
        'topics',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('course_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('importance', sa.Integer(), nullable=True, default=1),
        sa.Column('mastery', sa.Float(), nullable=True, default=0.0),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topics_course_id', 'topics', ['course_id'])

    # Create study_plans table
    op.create_table(
        'study_plans',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('course_id', sa.Uuid(), nullable=False),
        sa.Column('plan_json', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_study_plans_course_id', 'study_plans', ['course_id'])

    # Create topic_contents table
    op.create_table(
        'topic_contents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('topic_id', sa.Uuid(), nullable=False),
        sa.Column('notes_json', sa.JSON(), nullable=True),
        sa.Column('explanation_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('topic_id')
    )

    # Create quiz_attempts table
    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('topic_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_json', sa.JSON(), nullable=False),
        sa.Column('answers_json', sa.JSON(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_attempts_topic_id', 'quiz_attempts', ['topic_id'])

    # Create uploaded_docs table
    op.create_table(
        'uploaded_docs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('course_id', sa.Uuid(), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=True, default=0),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_uploaded_docs_course_id', 'uploaded_docs', ['course_id'])

    # Create runs table
    op.create_table(
        'runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('course_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, default='running'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_runs_course_id', 'runs', ['course_id'])


def downgrade() -> None:
    op.drop_table('runs')
    op.drop_table('uploaded_docs')
    op.drop_table('quiz_attempts')
    op.drop_table('topic_contents')
    op.drop_table('study_plans')
    op.drop_table('topics')
    op.drop_table('courses')