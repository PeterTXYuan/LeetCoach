"""create stable problem metadata

Revision ID: 0001
Revises: none
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('problems',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('approaches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('approach_key', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('pattern', sa.String(length=255), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.Column('thinking_steps', sa.JSON(), nullable=False),
    sa.CheckConstraint('display_order > 0', name='ck_approach_display_order'),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('problem_id', 'approach_key', name='uq_approach_problem_key')
    )
    with op.batch_alter_table('approaches', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_approaches_problem_id'), ['problem_id'], unique=False)

    op.create_table('related_problems',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('difficulty', sa.String(length=10), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('category', sa.String(length=10), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.CheckConstraint("category IN ('easier', 'similar', 'harder')", name='ck_related_category'),
    sa.CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name='ck_related_difficulty'),
    sa.CheckConstraint('display_order > 0', name='ck_related_display_order'),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('problem_id', 'slug', name='uq_related_problem_slug')
    )
    with op.batch_alter_table('related_problems', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_related_problems_problem_id'), ['problem_id'], unique=False)

    op.create_table('recognition_signal_sets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('approach_id', sa.Integer(), nullable=False),
    sa.Column('quote', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['approach_id'], ['approaches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('approach_id')
    )
    op.create_table('recognition_signal_bullets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('signal_set_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('display_order > 0', name='ck_signal_display_order'),
    sa.ForeignKeyConstraint(['signal_set_id'], ['recognition_signal_sets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('signal_set_id', 'display_order', name='uq_signal_set_order')
    )


def downgrade():
    op.drop_table('recognition_signal_bullets')
    op.drop_table('recognition_signal_sets')
    with op.batch_alter_table('related_problems', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_related_problems_problem_id'))

    op.drop_table('related_problems')
    with op.batch_alter_table('approaches', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_approaches_problem_id'))

    op.drop_table('approaches')
    op.drop_table('problems')
