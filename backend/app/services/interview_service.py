import random
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session


from app.models.answer_evaluation import AnswerEvaluation
from app.services.ai_interview_service import (
    evaluate_answer,
    generate_followup_question,
)
from app.models import (
    InterviewSession,
    JobProfile,
    QuestionBank,
    SessionQuestion,
    User,
)

from app.services.storage import (
    download_interview_video,
    upload_interview_video,
)
from app.services.transcription import is_whisper_sync_enabled, transcribe_video



from app.agents.agent_decision import AgentAction
from app.agents.interview_agent import InterviewAgent
from app.agents.interview_state import InterviewState

MAX_FOLLOWUPS_PER_INTERVIEW = 5
INTERVIEW_AGENT = InterviewAgent()

# =========================================================
# CREATE INTERVIEW
# =========================================================

def create_interview_session(
    db: Session,
    user_id: uuid.UUID,
    job_profile_id: uuid.UUID,
) -> InterviewSession:

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise ValueError("User not found.")

    job_profile = db.scalar(
        select(JobProfile).where(
            JobProfile.id == job_profile_id,
            JobProfile.is_active.is_(True),
        )
    )

    if job_profile is None:
        raise ValueError(
            "Job profile not found or inactive."
        )

    questions = db.scalars(
        select(QuestionBank).where(
            QuestionBank.job_profile_id == job_profile_id,
            QuestionBank.is_active.is_(True),
        )
    ).all()

    if len(questions) < 7:
        raise ValueError(
            "Not enough active questions available "
            "for this job profile."
        )

    # ---------------------------------------------------------
    # BASELINE HR QUESTIONS
    #
    # These questions are asked before the technical interview.
    # They are stored as SessionQuestion records so their
    # recordings/transcripts can later be used for soft-skill
    # analysis.
    #
    # They are NOT technical questions.
    # ---------------------------------------------------------

    baseline_questions = [
        "Tell me about yourself and why are you interested in this role?",
        
    ]

    # ---------------------------------------------------------
    # TECHNICAL QUESTIONS
    #
    # target_question_count continues to represent the number
    # of technical questions in the interview.
    # ---------------------------------------------------------

    target_count = random.randint(6, 7)

    selected_questions = random.sample(
        questions,
        target_count,
    )

    # ---------------------------------------------------------
    # CREATE INTERVIEW SESSION
    # ---------------------------------------------------------

    session = InterviewSession(
        user_id=user_id,
        job_profile_id=job_profile_id,
        status="in_progress",
        target_question_count=target_count,
    )

    db.add(session)
    db.flush()

    # ---------------------------------------------------------
    # CREATE BASELINE QUESTIONS FIRST
    # ---------------------------------------------------------

    question_order = 1

    for question_text in baseline_questions:

        session_question = SessionQuestion(
            session_id=session.id,
            question_order=question_order,
            question_text=question_text,
            source="baseline",
            source_question_id=None,
        )

        db.add(session_question)

        question_order += 1

    # ---------------------------------------------------------
    # CREATE TECHNICAL QUESTIONS AFTER BASELINE
    # ---------------------------------------------------------

    for question in selected_questions:

        session_question = SessionQuestion(
            session_id=session.id,
            question_order=question_order,
            question_text=question.question_text,
            source="bank",
            source_question_id=question.id,
        )

        db.add(session_question)

        question_order += 1

    db.commit()
    db.refresh(session)

    return session
# =========================================================
# CURRENT QUESTION
# =========================================================

def get_current_question(
    db: Session,
    session_id: uuid.UUID,
) -> SessionQuestion:

    session = db.scalar(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
        )
    )

    if session is None:
        raise ValueError(
            "Interview session not found."
        )

    if session.status != "in_progress":
        raise ValueError(
            "Interview session is not in progress."
        )

    current_question = db.scalar(
        select(SessionQuestion)
        .where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.answered_at.is_(None),
        )
        .order_by(
            SessionQuestion.question_order.asc()
        )
    )

    if current_question is None:
        raise ValueError(
            "No unanswered question remains."
        )

    return current_question


# =========================================================
# ANSWER QUESTION
# =========================================================

def submit_question_answer(
    db: Session,
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    transcript_text: str,
    time_taken_seconds: int | None = None,
    video_file=None,
):
    # ---------------------------------------------------------
    # Verify interview session
    # ---------------------------------------------------------

    session = db.scalar(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
        )
    )

    if session is None:
        raise ValueError("Interview session not found.")

    if session.status != "in_progress":
        raise ValueError("Interview session is not in progress.")

    # ---------------------------------------------------------
    # Find question
    # ---------------------------------------------------------

    question = db.scalar(
        select(SessionQuestion).where(
            SessionQuestion.id == question_id,
            SessionQuestion.session_id == session_id,
        )
    )

    if question is None:
        raise ValueError(
            "Question not found in this interview session."
        )

    # ---------------------------------------------------------
    # Prevent duplicate answers
    # ---------------------------------------------------------

    if question.answered_at is not None:
        raise ValueError("Question has already been answered.")

    # ---------------------------------------------------------
    # Save candidate answer
    # ---------------------------------------------------------

        

    question.transcript_text = transcript_text
    question.transcript_source = "browser"
    question.time_taken_seconds = time_taken_seconds

    job_profile = db.scalar(
        select(JobProfile).where(
            JobProfile.id == session.job_profile_id
        )
    )
    if job_profile is None:
        raise ValueError("Job profile not found.")

    video_object_name = None
    if video_file is not None:
        try:
            video_object_name = upload_interview_video(
                video_file=video_file,
                session_id=session_id,
                question_id=question_id,
        )

            question.video_url = video_object_name

        except Exception as error:
            db.rollback()

            raise RuntimeError(
                f"Failed to store interview video: {error}"
        )

    if video_object_name and is_whisper_sync_enabled():
        try:
            with tempfile.TemporaryDirectory(prefix="hiresense_whisper_sync_") as directory:
                video_path = Path(directory) / "interview.webm"
                download_interview_video(video_object_name, str(video_path))
                transcription = transcribe_video(
                    video_path,
                    role=job_profile.title,
                    skills=job_profile.skills or [],
                    question=question.question_text,
                )
            question.transcript_whisper = transcription["text"]
            question.transcript_confidence = transcription["confidence"]
            if transcription["text"]:
                question.transcript_source = "whisper"
                transcript_text = transcription["text"]
        except Exception as error:
            db.rollback()
            raise RuntimeError(f"Synchronous Whisper transcription failed: {error}") from error

    question.answered_at = datetime.now(timezone.utc)
    
   

    # ---------------------------------------------------------
    # EVALUATE ANSWER
    #
    # Every answered question is evaluated.
    #
    # Bank question:
    #   evaluation_type = "bank"
    #
    # AI follow-up:
    #   evaluation_type = "ai_followup"
    # ---------------------------------------------------------

    evaluation_type = question.source

    try:
        evaluation = evaluate_answer(
            question_text=question.question_text,
            answer_text=transcript_text,
            evaluation_type=evaluation_type,
        )

    except Exception as error:
        # AI evaluation failure should not destroy the interview.
        # Save the answer, but continue without evaluation.
        evaluation = None

    # ---------------------------------------------------------
    # Store evaluation
    # ---------------------------------------------------------

    if evaluation is not None:

        answer_evaluation = AnswerEvaluation(
            session_question_id=question.id,
            evaluation_type=evaluation_type,
            rating=evaluation.rating,
            correctness=evaluation.correctness,
            relevance=evaluation.relevance,
            completeness=evaluation.completeness,
            clarity=evaluation.clarity,
            coherence=evaluation.coherence,
            technical_understanding=evaluation.technical_understanding,
            verdict=evaluation.verdict,
            feedback=evaluation.feedback,
        )

        db.add(answer_evaluation)

    # ---------------------------------------------------------
    # AI FOLLOW-UP QUESTION
    #
    # Follow-ups can NEVER generate another follow-up.
    # ---------------------------------------------------------

    if question.source == "ai_followup":

        next_question = db.scalar(
            select(SessionQuestion)
            .where(
                SessionQuestion.session_id == session_id,
                SessionQuestion.answered_at.is_(None),
                SessionQuestion.source == "bank",
            )
            .order_by(
                SessionQuestion.question_order.asc()
            )
        )

        # No bank questions remain
        if next_question is None:

            session.status = "completed"
            session.ended_at = datetime.now(timezone.utc)

            db.commit()

            db.refresh(session)
            db.refresh(question)

            return session, question, None

        db.commit()

        db.refresh(session)
        db.refresh(question)
        db.refresh(next_question)

        return session, question, next_question

        # ---------------------------------------------------------
    # BANK QUESTION
    #
    # Let the Interview Agent decide what should happen next.
    #
    # IMPORTANT:
    # The technical evaluator still measures the answer.
    # The Interview Agent only interprets that result and
    # decides whether to ask a follow-up or continue.
    #
    # The existing follow-up generator and database logic
    # remain unchanged.
    # ---------------------------------------------------------

    if question.source == "bank":

        technical_score = None
        needs_followup = False

        if evaluation is not None:
            technical_score = getattr(
                evaluation,
                "rating",
                None,
            )

            needs_followup = bool(
                getattr(
                    evaluation,
                    "needs_followup",
                    False,
                )
            )

        # Count follow-ups that have actually been answered.
        # This prevents an unattempted/generated follow-up from
        # being counted as already used.
        answered_followups = db.scalars(
            select(SessionQuestion).where(
                SessionQuestion.session_id == session_id,
                SessionQuestion.source == "ai_followup",
                SessionQuestion.answered_at.is_not(None),
            )
        ).all()

        followups_used = len(answered_followups)

        # question_order is used as the current interview
        # progress indicator.
        questions_asked = question.question_order

        # ---------------------------------------------------------
        # BUILD INTERVIEW MEMORY
        # ---------------------------------------------------------
        #
        # Collect the answered questions from the current interview
        # so the agent can see how the candidate has performed over
        # time instead of only seeing the current answer.
        #
        # We only use information already available in the database.
        # We do not invent topics, strengths, or weaknesses here.
        # ---------------------------------------------------------

        answered_questions = db.scalars(
            select(SessionQuestion)
            .where(
                SessionQuestion.session_id == session_id,
                SessionQuestion.answered_at.is_not(None),
            )
            .order_by(
                SessionQuestion.question_order.asc()
            )
        ).all()

        question_history = []
        technical_scores = []

        recent_strengths = []
        recent_weaknesses = []

        for answered_question in answered_questions:

            # -------------------------------------------------
            # Get the evaluation for this answered question.
            #
            # For the current question, use the evaluation
            # already calculated above.
            #
            # For previous questions, read the stored
            # AnswerEvaluation record.
            # -------------------------------------------------

            if answered_question.id == question.id:
                current_evaluation = evaluation
            else:
                current_evaluation = db.scalar(
                    select(AnswerEvaluation).where(
                        AnswerEvaluation.session_question_id
                        == answered_question.id
                    )
                )

            current_score = (
                getattr(
                    current_evaluation,
                    "rating",
                    None,
                )
                if current_evaluation is not None
                else None
            )

            # -------------------------------------------------
            # Build structured question history.
            #
            # This gives the agent more context than just the
            # current answer.
            # -------------------------------------------------

            history_item = {
                "question": answered_question.question_text,
                "source": answered_question.source,
                "question_order": answered_question.question_order,
                "score": current_score,
            }

            if current_evaluation is not None:
                history_item.update(
                    {
                        "correctness": getattr(
                            current_evaluation,
                            "correctness",
                            None,
                        ),
                        "relevance": getattr(
                            current_evaluation,
                            "relevance",
                            None,
                        ),
                        "completeness": getattr(
                            current_evaluation,
                            "completeness",
                            None,
                        ),
                        "clarity": getattr(
                            current_evaluation,
                            "clarity",
                            None,
                        ),
                        "coherence": getattr(
                            current_evaluation,
                            "coherence",
                            None,
                        ),
                        "technical_understanding": getattr(
                            current_evaluation,
                            "technical_understanding",
                            None,
                        ),
                        "verdict": getattr(
                            current_evaluation,
                            "verdict",
                            None,
                        ),
                    }
                )

            question_history.append(history_item)

            # -------------------------------------------------
            # Store technical score history.
            # -------------------------------------------------

            if current_score is not None:
                technical_scores.append(
                    float(current_score)
                )

            # -------------------------------------------------
            # Detect measurable strengths and weaknesses.
            #
            # We use the evaluator's existing numeric fields.
            # We do NOT invent psychological conclusions.
            # -------------------------------------------------

            if current_evaluation is not None:

                evaluation_scores = []

                for field_name in (
                    "rating",
                    "correctness",
                    "relevance",
                    "completeness",
                    "clarity",
                    "coherence",
                    "technical_understanding",
                ):
                    value = getattr(
                        current_evaluation,
                        field_name,
                        None,
                    )

                    if value is not None:
                        try:
                            evaluation_scores.append(
                                float(value)
                            )
                        except (
                            TypeError,
                            ValueError,
                        ):
                            pass

                if evaluation_scores:

                    average_score = (
                        sum(evaluation_scores)
                        / len(evaluation_scores)
                    )

                    if average_score >= 7:
                        recent_strengths.append(
                            f"Strong performance on: "
                            f"{answered_question.question_text}"
                        )

                    elif average_score <= 4:
                        recent_weaknesses.append(
                            f"Weak performance on: "
                            f"{answered_question.question_text}"
                        )

        # -----------------------------------------------------
        # Keep only recent patterns.
        #
        # The agent does not need the entire interview's
        # strength/weakness descriptions in its small context.
        # -----------------------------------------------------

        recent_strengths = recent_strengths[-3:]
        recent_weaknesses = recent_weaknesses[-3:]

        # -----------------------------------------------------
        # Topics are intentionally not inferred from question
        # text here.
        #
        # The current question/session models do not provide a
        # verified topic field in the information available to
        # this service, so we avoid inventing topics.
        # -----------------------------------------------------

        topics_covered = []


        

        # JobProfile is already loaded above.
        #
        # The current InterviewAgent does not make a decision
        # based on difficulty yet, so we safely read it if the
        # model contains the field and otherwise use "unknown".
        difficulty = getattr(
            job_profile,
            "difficulty",
            "unknown",
        )

        # target_question_count represents the technical question
        # budget created when the interview session was initialized.
        question_budget = getattr(
            session,
            "target_question_count",
            None,
        )

        interview_state = InterviewState(
            role=job_profile.title,
            difficulty=difficulty,
            current_question=question.question_text,
            current_answer=transcript_text,
            technical_score=technical_score,
            needs_followup=needs_followup,
            questions_asked=questions_asked,
            followups_used=followups_used,
            topics_covered=topics_covered,
            question_history=question_history,
            technical_scores=technical_scores,
            recent_strengths=recent_strengths,
            recent_weaknesses=recent_weaknesses,
            question_budget=question_budget,
            metadata={
                "current_question_source": question.source,
                "current_evaluation_type": evaluation_type,
            },
        )

        agent_decision = INTERVIEW_AGENT.decide(
            interview_state
        )
        print(
            "[INTERVIEW-AGENT]",
            f"action={agent_decision.action.value}",
            f"technical_score={technical_score}",
            f"needs_followup={needs_followup}",
            f"followups_used={followups_used}",
            f"questions_asked={interview_state.questions_asked}",
            f"question_budget={interview_state.question_budget}",
            f"technical_scores={interview_state.technical_scores}",
            f"recent_strengths={interview_state.recent_strengths}",
            f"recent_weaknesses={interview_state.recent_weaknesses}",
            f"reason={agent_decision.reason}",
        )



        # -----------------------------------------------------
        # Agent says: FINISH
        # -----------------------------------------------------

        if agent_decision.action == AgentAction.FINISH:

            session.status = "completed"
            session.ended_at = datetime.now(timezone.utc)

            db.commit()

            db.refresh(session)
            db.refresh(question)

            return session, question, None


        # -----------------------------------------------------
        # Agent says: ASK_FOLLOWUP
        # -----------------------------------------------------

        if agent_decision.action == AgentAction.ASK_FOLLOWUP:

            # -------------------------------------------------
            # Check whether this bank question already has a
            # follow-up.
            # -------------------------------------------------

            existing_followup = db.scalar(
                select(SessionQuestion).where(
                    SessionQuestion.parent_session_question_id
                    == question.id
                )
            )

            if existing_followup is None:

                try:

                    followup_text = generate_followup_question(
                        question_text=question.question_text,
                        answer_text=transcript_text,
                        job_profile=job_profile.title,
                        followup_instruction=agent_decision.followup_instruction,
                    )

                except Exception:
                    followup_text = None

                if followup_text:

                    # -----------------------------------------
                    # Shift later questions
                    # -----------------------------------------

                    db.query(SessionQuestion).filter(
                        SessionQuestion.session_id == session_id,
                        SessionQuestion.question_order
                        > question.question_order,
                    ).update(
                        {
                            SessionQuestion.question_order:
                            SessionQuestion.question_order + 1
                        },
                        synchronize_session=False,
                    )

                    # -----------------------------------------
                    # Create follow-up question
                    # -----------------------------------------

                    followup = SessionQuestion(
                        session_id=session_id,
                        question_order=question.question_order + 1,
                        question_text=followup_text,
                        source="ai_followup",
                        source_question_id=None,
                        parent_session_question_id=question.id,
                    )

                    db.add(followup)

                    db.commit()

                    db.refresh(session)
                    db.refresh(question)
                    db.refresh(followup)

                    return session, question, followup






    # ---------------------------------------------------------
    # Normal next bank question
    # ---------------------------------------------------------

    
    next_question = db.scalar(
        select(SessionQuestion)
        .where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.answered_at.is_(None),
            SessionQuestion.source == "bank",
            SessionQuestion.id != question.id,
        )
        .order_by(
            SessionQuestion.question_order.asc()
        )
    )
    # ---------------------------------------------------------
    # Complete interview
    # ---------------------------------------------------------

    if next_question is None:

        session.status = "completed"
        session.ended_at = datetime.now(timezone.utc)

        db.commit()

        db.refresh(session)
        db.refresh(question)

        return session, question, None

    # ---------------------------------------------------------
    # Continue interview
    # ---------------------------------------------------------

    db.commit()

    db.refresh(session)
    db.refresh(question)
    db.refresh(next_question)

    return session, question, next_question