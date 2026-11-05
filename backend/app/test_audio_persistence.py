from uuid import UUID

import app.services.audio_persistence as audio_persistence


class FakeQuery:
    def __init__(self, evaluation):
        self.evaluation = evaluation

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.evaluation


class FakeDB:
    def __init__(self):
        self.evaluation = None
        self.added_objects = []
        self.committed = False
        self.refreshed_object = None

    def query(self, model):
        return FakeQuery(self.evaluation)

    def add(self, obj):
        self.added_objects.append(obj)
        self.evaluation = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed_object = obj


class FakeAudioEvaluation:
    # Class-level field so the production query expression:
    # AudioEvaluation.session_question_id == session_question_id
    # can be constructed by the fake model.
    session_question_id = object()

    def __init__(self, session_question_id):
        self.session_question_id = session_question_id
        self.overall_score = None
        self.pace = None
        self.fluency = None
        self.volume = None
        self.speaking_clarity = None
        self.articulation = None
        self.vocal_confidence = None
        self.filler_word_score = None
        self.hesitation_score = None
        self.words_per_minute = None
        self.pause_count = None
        self.total_pause_seconds = None
        self.filler_word_count = None
        self.hesitation_count = None
        self.analysis_status = None
        self.error_message = None
        self.analyzed_at = None


def test_save_audio_evaluation_persists_scores_and_features(monkeypatch):
    """
    Verify that the persistence layer maps extracted audio features
    and calculated scores into AudioEvaluation correctly.

    This test does not require PostgreSQL or Docker.
    """

    monkeypatch.setattr(
        audio_persistence,
        "AudioEvaluation",
        FakeAudioEvaluation,
    )

    db = FakeDB()

    session_question_id = UUID(
        "e534c4bf-ea30-484d-94fc-24673d4fc5f3"
    )

    features = {
        "words_per_minute": 125.0,
        "pause_count": 2,
        "total_pause_seconds": 1.0,
        "filler_word_count": 2,
        "hesitation_count": 1,
    }

    scores = {
        "overall_score": 9.0,
        "pace": 10.0,
        "fluency": 9.5,
        "vocal_energy": 8.0,
        "filler_word_score": 8.0,
        "hesitation_score": 8.0,
    }

    evaluation = audio_persistence.save_audio_evaluation(
        db=db,
        session_question_id=session_question_id,
        features=features,
        scores=scores,
    )

    assert evaluation.session_question_id == session_question_id

    # Overall score
    assert evaluation.overall_score == 9

    # Score mappings
    assert evaluation.pace == 10.0
    assert evaluation.fluency == 9.5
    assert evaluation.volume == 8.0

    # Raw feature mappings
    assert evaluation.words_per_minute == 125.0
    assert evaluation.pause_count == 2
    assert evaluation.total_pause_seconds == 1.0
    assert evaluation.filler_word_count == 2

    # Existing filler score mapping
    assert evaluation.filler_word_score == 8.0

    # Analysis state
    assert evaluation.analysis_status == "completed"
    assert evaluation.error_message is None
    assert evaluation.analyzed_at is not None

    # DB lifecycle
    assert len(db.added_objects) == 1
    assert db.committed is True
    assert db.refreshed_object is evaluation


def test_save_audio_evaluation_requires_overall_score(monkeypatch):
    """
    The persistence layer must reject incomplete scoring results
    instead of saving an evaluation without an overall score.
    """

    monkeypatch.setattr(
        audio_persistence,
        "AudioEvaluation",
        FakeAudioEvaluation,
    )

    db = FakeDB()

    session_question_id = UUID(
        "e534c4bf-ea30-484d-94fc-24673d4fc5f3"
    )

    features = {
        "words_per_minute": 125.0,
    }

    scores = {
        "pace": 10.0,
        "fluency": 9.5,
    }

    try:
        audio_persistence.save_audio_evaluation(
            db=db,
            session_question_id=session_question_id,
            features=features,
            scores=scores,
        )
        assert False, "Expected ValueError was not raised"
    except ValueError as exc:
        assert str(exc) == (
            "Cannot save audio evaluation without an overall audio score."
        )