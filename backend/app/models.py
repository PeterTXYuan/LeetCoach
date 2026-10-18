"""Stable editorial metadata. Public approach IDs are keys, never DB IDs."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="ck_problem_difficulty"),
        UniqueConstraint("leetcode_number", name="uq_problem_leetcode_number"),
        CheckConstraint("leetcode_number IS NULL OR leetcode_number > 0", name="ck_problem_leetcode_number"),
        CheckConstraint("time_limit_ms IS NULL OR time_limit_ms > 0", name="ck_problem_time_limit"),
        CheckConstraint("memory_limit_mb IS NULL OR memory_limit_mb > 0", name="ck_problem_memory_limit"),
        CheckConstraint("description_source_type IS NULL OR description_source_type IN ('curated_restatement', 'official', 'authorized')", name="ck_problem_source_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(10))
    summary: Mapped[str] = mapped_column(Text)
    leetcode_number: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    description_source_url: Mapped[str | None] = mapped_column(Text)
    description_source_type: Mapped[str | None] = mapped_column(String(32))
    description_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_limit_ms: Mapped[int | None] = mapped_column(Integer)
    memory_limit_mb: Mapped[int | None] = mapped_column(Integer)
    time_complexity_instruction: Mapped[str | None] = mapped_column(Text)
    space_complexity_instruction: Mapped[str | None] = mapped_column(Text)
    approaches: Mapped[list["Approach"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="Approach.display_order"
    )
    related_problems: Mapped[list["RelatedProblem"]] = relationship(
        cascade="all, delete-orphan", order_by="RelatedProblem.display_order"
    )
    constraints: Mapped[list["ProblemConstraint"]] = relationship(
        cascade="all, delete-orphan", order_by="ProblemConstraint.display_order"
    )
    examples: Mapped[list["ProblemExample"]] = relationship(
        cascade="all, delete-orphan", order_by="ProblemExample.display_order"
    )
    submission_templates: Mapped[list["ProblemSubmissionTemplate"]] = relationship(
        cascade="all, delete-orphan", order_by="ProblemSubmissionTemplate.language"
    )


class ProblemConstraint(Base):
    __tablename__ = "problem_constraints"
    __table_args__ = (
        UniqueConstraint("problem_id", "display_order", name="uq_problem_constraint_order"),
        CheckConstraint("display_order > 0", name="ck_problem_constraint_display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    display_order: Mapped[int]


class ProblemExample(Base):
    __tablename__ = "problem_examples"
    __table_args__ = (
        UniqueConstraint("problem_id", "display_order", name="uq_problem_example_order"),
        CheckConstraint("display_order > 0", name="ck_problem_example_display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    input_text: Mapped[str] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int]


class ProblemSubmissionTemplate(Base):
    __tablename__ = "problem_submission_templates"
    __table_args__ = (
        UniqueConstraint("problem_id", "language", name="uq_problem_submission_language"),
        CheckConstraint(
            "language IN ('python', 'java', 'javascript', 'cpp')",
            name="ck_problem_submission_language",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(Text)


class Approach(Base):
    __tablename__ = "approaches"
    __table_args__ = (
        UniqueConstraint("problem_id", "approach_key", name="uq_approach_problem_key"),
        CheckConstraint("display_order > 0", name="ck_approach_display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    approach_key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    pattern: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    display_order: Mapped[int]
    thinking_steps: Mapped[list[str]] = mapped_column(JSON)
    problem: Mapped[Problem] = relationship(back_populates="approaches")
    recognition_signals: Mapped["RecognitionSignals | None"] = relationship(
        cascade="all, delete-orphan", single_parent=True
    )


class RecognitionSignals(Base):
    __tablename__ = "recognition_signal_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    approach_id: Mapped[int] = mapped_column(
        ForeignKey("approaches.id", ondelete="CASCADE"), unique=True
    )
    quote: Mapped[str | None] = mapped_column(Text)
    bullets: Mapped[list["RecognitionSignalBullet"]] = relationship(
        cascade="all, delete-orphan", order_by="RecognitionSignalBullet.display_order"
    )


class RecognitionSignalBullet(Base):
    __tablename__ = "recognition_signal_bullets"
    __table_args__ = (
        UniqueConstraint("signal_set_id", "display_order", name="uq_signal_set_order"),
        CheckConstraint("display_order > 0", name="ck_signal_display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_set_id: Mapped[int] = mapped_column(ForeignKey("recognition_signal_sets.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    display_order: Mapped[int]


class RelatedProblem(Base):
    __tablename__ = "related_problems"
    __table_args__ = (
        UniqueConstraint("problem_id", "slug", name="uq_related_problem_slug"),
        CheckConstraint("category IN ('easier', 'similar', 'harder')", name="ck_related_category"),
        CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="ck_related_difficulty"),
        CheckConstraint("display_order > 0", name="ck_related_display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    # Targets can be outside the supported dataset; this is an editorial card,
    # not a foreign key to another supported problem or a recommendation graph.
    slug: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(10))
    display_order: Mapped[int]
