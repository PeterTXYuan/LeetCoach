import os
from unittest.mock import patch

from db_test_support import DatabaseTestCase
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import BACKEND_DIR, create_database_engine, get_database_url
from app.main import UNAVAILABLE_DETAIL
from app.mock_data import PROBLEM_ANALYSES
from app.models import Approach, Problem, RecognitionSignalBullet, RecognitionSignals, RelatedProblem
from app.seed import seed_data
from app.services.problem_repository import find_problem_analysis
from app.stable_data import CURATED_PROBLEMS, CURATED_RELATED_PROBLEMS

TABLE_MODELS = (Problem, Approach, RecognitionSignals, RecognitionSignalBullet, RelatedProblem)


def public_problem_analysis(problem):
    """The pre-database response contract, independently of the new serializer."""
    return {"slug": problem["slug"], "approaches": [
        {key: value for key, value in approach.items() if key != "hints"}
        for approach in sorted(problem["approaches"], key=lambda a: a["displayOrder"])
    ]}


class DatabaseTests(DatabaseTestCase):
    def snapshot_ids(self):
        with Session(self.engine) as session:
            return {model.__tablename__: list(session.scalars(select(model.id).order_by(model.id)))
                    for model in TABLE_MODELS}

    def test_existing_api_payloads_are_unchanged(self):
        for slug, problem in CURATED_PROBLEMS.items():
            with self.subTest(slug=slug):
                response = self.client.get(f"/api/problems/{slug}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), public_problem_analysis(problem))
                response = self.client.get(f"/api/problems/{slug}/related")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"slug": slug, **CURATED_RELATED_PROBLEMS[slug]})

    def test_seed_repeats_preserve_counts_ids_and_restore_curated_content(self):
        before = self.snapshot_ids()
        self.assertEqual(len(before["problems"]), 20)
        with Session(self.engine) as session, session.begin():
            session.scalar(select(Approach)).summary = "Changed summary"
            session.scalar(select(RecognitionSignals)).quote = "Changed quote"
            session.scalar(select(RecognitionSignalBullet)).text = "Changed bullet"
            session.scalar(select(RelatedProblem)).title = "Changed related title"
            signals = session.scalar(select(RecognitionSignals))
            signals.bullets.append(RecognitionSignalBullet(display_order=99, text="Obsolete bullet"))
            session.add(Problem(slug="unrelated-local-record"))
        for _ in range(2):
            with Session(self.engine) as session, session.begin():
                seed_data(session)
        after = self.snapshot_ids()
        self.assertEqual(after["problems"][:20], before["problems"])
        self.assertEqual(len(after["problems"]), 21)
        for table in before.keys() - {"problems"}:
            self.assertEqual(after[table], before[table])
        self.test_existing_api_payloads_are_unchanged()

    def test_database_records_drive_lookups_and_canonical_order(self):
        # Use records not present in the fixtures, deliberately inserted out of order.
        with Session(self.engine) as session, session.begin():
            problem = Problem(slug="database-only")
            for key, order in [("second", 2), ("hash-map", 1)]:
                problem.approaches.append(Approach(
                    approach_key=key, name=key, pattern="DB pattern", summary="DB summary",
                    is_primary=order == 1, display_order=order, thinking_steps=["DB thinking"],
                    recognition_signals=RecognitionSignals(quote="DB quote", bullets=[
                        RecognitionSignalBullet(text="Second clue", display_order=2),
                        RecognitionSignalBullet(text="First clue", display_order=1),
                    ]),
                ))
            problem.related_problems = [RelatedProblem(
                slug=f"outside-{order}", title=f"Related {order}", difficulty="Easy",
                category="similar", display_order=order,
            ) for order in (2, 1)]
            session.add(problem)
        data = self.client.get("/api/problems/database-only").json()
        self.assertEqual([a["id"] for a in data["approaches"]], ["hash-map", "second"])
        self.assertEqual(data["approaches"][0]["summary"], "DB summary")
        self.assertEqual(data["approaches"][0]["recognitionSignals"], {
            "quote": "DB quote", "bullets": ["First clue", "Second clue"]
        })
        related = self.client.get("/api/problems/database-only/related").json()
        self.assertEqual(related["easier"], [])
        self.assertEqual(related["harder"], [])
        self.assertEqual([r["slug"] for r in related["similar"]], ["outside-1", "outside-2"])
        self.assertNotIn("reason", related["similar"][0])

    def test_unknown_or_deleted_problem_returns_existing_404_without_mock_fallback(self):
        with Session(self.engine) as session, session.begin():
            session.execute(delete(Problem).where(Problem.slug == "two-sum"))
        for slug in ("not-seeded", "two-sum"):
            for suffix in ("", "/related"):
                response = self.client.get(f"/api/problems/{slug}{suffix}")
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": UNAVAILABLE_DETAIL})

    def test_metadata_survives_reopening_sqlite(self):
        self.engine.dispose()
        reopened = create_database_engine(self.url)
        try:
            with Session(reopened) as session:
                self.assertEqual(find_problem_analysis(session, "two-sum"),
                                 public_problem_analysis(CURATED_PROBLEMS["two-sum"]))
        finally:
            reopened.dispose()

    def test_seed_failure_rolls_back_all_changes(self):
        before = self.snapshot_ids()
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.execute(delete(Problem))
                seed_data(session)
                session.add(Problem(slug="two-sum"))
        self.assertEqual(self.snapshot_ids(), before)
        self.test_existing_api_payloads_are_unchanged()

    def test_recognition_and_related_constraints(self):
        with Session(self.engine) as session:
            signals = session.scalar(select(RecognitionSignals))
            approach_id, signal_set_id = signals.approach_id, signals.id
            related = session.scalar(select(RelatedProblem))
            attributes = {column.name: getattr(related, column.name)
                          for column in RelatedProblem.__table__.columns if column.name != "id"}
        for record in (
            RecognitionSignals(approach_id=approach_id),
            RecognitionSignalBullet(signal_set_id=signal_set_id, display_order=1, text="Duplicate"),
            RelatedProblem(**attributes),
            RelatedProblem(**{**attributes, "slug": "invalid", "category": "prerequisite"}),
            RelatedProblem(**{**attributes, "slug": "invalid", "difficulty": "Unknown"}),
        ):
            with self.subTest(record=type(record).__name__), self.assertRaises(IntegrityError):
                with Session(self.engine) as session, session.begin():
                    session.add(record)

    def test_mock_guidance_routes_keep_their_existing_payloads(self):
        from app.services.solution_service import generate_approach_solution

        for slug, problem in PROBLEM_ANALYSES.items():
            primary = next(a for a in problem["approaches"] if a["isPrimary"])
            self.assertEqual(self.client.get(f"/api/problems/{slug}/hints").json(), {
                "slug": slug, "approachId": primary["id"], "hints": primary["hints"]
            })
            for approach in problem["approaches"]:
                endpoint = f"/api/problems/{slug}/approaches/{approach['id']}"
                self.assertEqual(self.client.get(f"{endpoint}/hints").json(), {
                    "slug": slug, "approachId": approach["id"], "hints": approach["hints"]
                })
                for language in ("python", "java", "javascript", "cpp"):
                    with self.subTest(slug=slug, approach=approach["id"], language=language):
                        response = self.client.post(f"{endpoint}/solution", json={"language": language})
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json(), generate_approach_solution(problem, approach, language))

    def test_expanded_database_problem_does_not_gain_mock_guidance(self):
        slug = "contains-duplicate"
        self.assertEqual(self.client.get(f"/api/problems/{slug}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/problems/{slug}/related").status_code, 200)
        self.assertEqual(self.client.get(f"/api/problems/{slug}/hints").status_code, 404)
        for path, body in (
            ("hash-set/hints", None),
            ("hash-set/starter-code", {"language": "python", "level": 1}),
            ("hash-set/solution", {"language": "python"}),
        ):
            endpoint = f"/api/problems/{slug}/approaches/{path}"
            response = self.client.get(endpoint) if body is None else self.client.post(endpoint, json=body)
            self.assertEqual(response.status_code, 404)

    def test_database_enforces_uniqueness_and_foreign_keys(self):
        with Session(self.engine) as session:
            approach = session.scalar(select(Approach).where(Approach.approach_key == "hash-map"))
            attributes = {column.name: getattr(approach, column.name)
                          for column in Approach.__table__.columns if column.name != "id"}
        for record in (
            Problem(slug="two-sum"),
            Approach(**attributes),
            Approach(**{**attributes, "problem_id": -1}),
            RecognitionSignals(approach_id=-1),
            RecognitionSignalBullet(signal_set_id=-1, text="Orphan", display_order=1),
            RelatedProblem(problem_id=-1, slug="orphan", title="Orphan", difficulty="Easy",
                           category="easier", display_order=1),
        ):
            with self.subTest(record=type(record).__name__), self.assertRaises(IntegrityError):
                with Session(self.engine) as session, session.begin():
                    session.add(record)
        # The same canonical key is legal on a different problem.
        with Session(self.engine) as session, session.begin():
            problem = Problem(slug="another-problem")
            session.add(problem)
            session.flush()
            session.add(Approach(**{**attributes, "problem_id": problem.id}))

    def test_deleting_a_problem_cascades_through_stable_metadata(self):
        with Session(self.engine) as session, session.begin():
            session.execute(delete(Problem))
        with Session(self.engine) as session:
            for model in TABLE_MODELS:
                self.assertEqual(session.scalar(select(func.count()).select_from(model)), 0)

    def test_migration_round_trip_and_model_consistency(self):
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.check(config)
        self.migrate("downgrade", "base")
        self.assertEqual(set(inspect(self.engine).get_table_names()), {"alembic_version"})
        self.migrate("upgrade", "head")
        with Session(self.engine) as session, session.begin():
            seed_data(session)
        self.test_existing_api_payloads_are_unchanged()

    def test_relative_database_url_is_anchored_to_backend_directory(self):
        with patch.dict(os.environ, {"LEETCOACH_DATABASE_URL": "sqlite:///relative.db"}):
            self.assertEqual(get_database_url().database, str(BACKEND_DIR / "relative.db"))
