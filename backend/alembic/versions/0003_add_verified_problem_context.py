"""Add source-audited problem context without rewriting existing rows.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('problems') as batch_op:
        batch_op.add_column(sa.Column('leetcode_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('description_source_url', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('description_source_type', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('description_verified_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('time_limit_ms', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('memory_limit_mb', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('time_complexity_instruction', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('space_complexity_instruction', sa.Text(), nullable=True))
        batch_op.create_unique_constraint('uq_problem_leetcode_number', ['leetcode_number'])
        batch_op.create_check_constraint('ck_problem_leetcode_number', 'leetcode_number IS NULL OR leetcode_number > 0')
        batch_op.create_check_constraint('ck_problem_time_limit', 'time_limit_ms IS NULL OR time_limit_ms > 0')
        batch_op.create_check_constraint('ck_problem_memory_limit', 'memory_limit_mb IS NULL OR memory_limit_mb > 0')
        batch_op.create_check_constraint('ck_problem_source_type', "description_source_type IS NULL OR description_source_type IN ('curated_restatement', 'official', 'authorized')")


def downgrade():
    with op.batch_alter_table('problems') as batch_op:
        batch_op.drop_constraint('ck_problem_source_type', type_='check')
        batch_op.drop_constraint('ck_problem_memory_limit', type_='check')
        batch_op.drop_constraint('ck_problem_time_limit', type_='check')
        batch_op.drop_constraint('ck_problem_leetcode_number', type_='check')
        batch_op.drop_constraint('uq_problem_leetcode_number', type_='unique')
        batch_op.drop_column('space_complexity_instruction')
        batch_op.drop_column('time_complexity_instruction')
        batch_op.drop_column('memory_limit_mb')
        batch_op.drop_column('time_limit_ms')
        batch_op.drop_column('description_verified_at')
        batch_op.drop_column('description_source_type')
        batch_op.drop_column('description_source_url')
        batch_op.drop_column('description')
        batch_op.drop_column('leetcode_number')
