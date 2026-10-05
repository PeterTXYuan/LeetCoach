"""add problem specification grounding data

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('problem_constraints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('display_order > 0', name='ck_problem_constraint_display_order'),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('problem_id', 'display_order', name='uq_problem_constraint_order')
    )
    with op.batch_alter_table('problem_constraints', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_problem_constraints_problem_id'), ['problem_id'], unique=False)

    op.create_table('problem_examples',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('input_text', sa.Text(), nullable=False),
    sa.Column('output_text', sa.Text(), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('display_order > 0', name='ck_problem_example_display_order'),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('problem_id', 'display_order', name='uq_problem_example_order')
    )
    with op.batch_alter_table('problem_examples', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_problem_examples_problem_id'), ['problem_id'], unique=False)

    op.create_table('problem_submission_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=20), nullable=False),
    sa.Column('code', sa.Text(), nullable=False),
    sa.CheckConstraint("language IN ('python', 'java', 'javascript', 'cpp')", name='ck_problem_submission_language'),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('problem_id', 'language', name='uq_problem_submission_language')
    )
    with op.batch_alter_table('problem_submission_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_problem_submission_templates_problem_id'), ['problem_id'], unique=False)

    # Temporary defaults allow upgrading an already-seeded 0001 database. The
    # explicit seed command replaces these placeholders immediately afterward.
    op.add_column('problems', sa.Column('title', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('problems', sa.Column('difficulty', sa.String(length=10), nullable=False, server_default='Easy'))
    op.add_column('problems', sa.Column('summary', sa.Text(), nullable=False, server_default=''))
    with op.batch_alter_table('problems', schema=None) as batch_op:
        batch_op.alter_column('title', server_default=None)
        batch_op.alter_column('difficulty', server_default=None)
        batch_op.alter_column('summary', server_default=None)
        batch_op.create_check_constraint(
            'ck_problem_difficulty', "difficulty IN ('Easy', 'Medium', 'Hard')"
        )


def downgrade():
    with op.batch_alter_table('problems', schema=None) as batch_op:
        batch_op.drop_constraint('ck_problem_difficulty', type_='check')
        batch_op.drop_column('summary')
        batch_op.drop_column('difficulty')
        batch_op.drop_column('title')

    with op.batch_alter_table('problem_submission_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_problem_submission_templates_problem_id'))

    op.drop_table('problem_submission_templates')
    with op.batch_alter_table('problem_examples', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_problem_examples_problem_id'))

    op.drop_table('problem_examples')
    with op.batch_alter_table('problem_constraints', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_problem_constraints_problem_id'))

    op.drop_table('problem_constraints')
