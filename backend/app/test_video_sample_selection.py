from types import SimpleNamespace
from uuid import uuid4

from app.services.video_sample_selection import select_video_samples


class _QueryResult:
    def __init__(self, questions):
        self.questions = questions

    def all(self):
        return self.questions


class _FakeSession:
    def __init__(self, questions):
        self.questions = questions

    def scalars(self, _query):
        return _QueryResult(self.questions)


def _question(order: int, duration: int, video_url: str | None = "video.webm"):
    return SimpleNamespace(
        id=uuid4(),
        question_order=order,
        video_url=video_url,
        time_taken_seconds=duration,
    )


def test_selects_all_recordings_when_fewer_than_five_are_available():
    questions = [_question(1, 32), _question(2, 48), _question(3, 41)]

    samples = select_video_samples(_FakeSession(questions), uuid4())

    assert len(samples) == 3
    assert [sample.question_order for sample in samples] == [1, 2, 3]


def test_selects_up_to_five_representative_recordings():
    questions = [_question(order, order * 10) for order in range(1, 9)]

    samples = select_video_samples(_FakeSession(questions), uuid4())

    assert len(samples) == 5
    assert len({sample.session_question_id for sample in samples}) == 5
    assert 8 in {sample.question_order for sample in samples}
    assert [sample.question_order for sample in samples] == sorted(
        sample.question_order for sample in samples
    )


def test_a_single_valid_video_is_usable_and_empty_recordings_return_none():
    valid = _question(1, 20)
    invalid = _question(2, 0)

    assert len(select_video_samples(_FakeSession([valid]), uuid4())) == 1
    assert select_video_samples(_FakeSession([invalid]), uuid4()) == []
