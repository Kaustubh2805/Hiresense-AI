import os
import uuid
import json
import logging
import threading
from uuid import UUID
from fastapi import BackgroundTasks, FastAPI, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session
import requests

from app.db.database import Base, SessionLocal, engine, get_db
from app.auth import get_current_user
from app.models import (
    Profile,
    User,
    JobProfile,
    InterviewSession,
    QuestionBank,
    AudioEvaluation,
    NLPEvaluation,
)
from app.schemas.interview import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionQuestionResponse,
    QuestionAnswerResponse,
)

from app.services.interview_service import (
    create_interview_session,
    get_current_question,
    submit_question_answer,
)

from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware



from app.services.video_analysis_pipeline import (
    analyze_session_videos,
    VideoAnalysisPipelineError,
)

from app.services.post_interview_analysis_service import (
    run_post_interview_analysis,
)
from app.services.nlp_analysis_pipeline import (
    analyze_session_question_nlp,
    NLPAnalysisPipelineError,
)
from app.services.transcription import (
    WHISPER_CONFIDENCE_FALLBACK_THRESHOLD,
    is_whisper_sync_enabled,
    is_transcript_usable,
    select_transcript,
)
from app.services.transcription_jobs import enqueue_transcription
from app.agents.insight_agent import InsightAgent
from app.models.session_question import SessionQuestion
from app.routes.auth import router as auth_router
from app.routes.account import router as account_router
from app.config import OLLAMA_MODEL, OLLAMA_URL

app = FastAPI(
    title="HireSense AI",
    description="AI-powered adaptive mock interview platform",
    version="1.0.0",
)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.100:3000",
        *[
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ],
    ],
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})"
        r"(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

with engine.begin() as connection:
    connection.execute(
        text(
            "ALTER TABLE question_bank "
            "ADD COLUMN IF NOT EXISTS difficulty "
            "VARCHAR NOT NULL DEFAULT 'Normal'"
        )
    )
    connection.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS parsed_resume JSONB"))
    connection.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS experience_years NUMERIC"))
    connection.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS resume_filename VARCHAR"))
    connection.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS resume_updated_at TIMESTAMPTZ"))
    connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS english_word_count INTEGER"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS english_word_ratio DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS english_words TEXT"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS code_switching_count INTEGER"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS code_switching_ratio DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS dominant_language VARCHAR"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS language_switching_examples TEXT"))
    connection.execute(text("ALTER TABLE nlp_evaluations ADD COLUMN IF NOT EXISTS word_language_identification TEXT"))
    connection.execute(
        text("ALTER TABLE job_profiles ADD COLUMN IF NOT EXISTS skills VARCHAR[] NOT NULL DEFAULT '{}'")
    )
    connection.execute(
        text("ALTER TABLE session_questions ADD COLUMN IF NOT EXISTS transcript_whisper TEXT")
    )
    connection.execute(
        text("ALTER TABLE session_questions ADD COLUMN IF NOT EXISTS transcript_source VARCHAR")
    )
    connection.execute(
        text("ALTER TABLE session_questions ADD COLUMN IF NOT EXISTS transcript_confidence DOUBLE PRECISION")
    )
    connection.execute(
        text("ALTER TABLE session_questions ADD COLUMN IF NOT EXISTS transcript_languages TEXT")
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS interview_insights (
                session_id UUID PRIMARY KEY REFERENCES interview_sessions(id) ON DELETE CASCADE,
                analysis_status VARCHAR NOT NULL DEFAULT 'pending',
                insights_json JSONB,
                timings_json JSONB,
                error_message TEXT,
                started_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS interview_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
                report_json JSONB,
                pdf_data TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
        )
    )
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS eye_contact DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS facial_expression DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS posture DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS head_movement DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS gestures DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS body_language DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS attentiveness DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS visual_confidence DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS eye_contact_percentage DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS face_visibility_percentage DOUBLE PRECISION"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS gesture_count INTEGER"))
    connection.execute(text("ALTER TABLE video_evaluations ADD COLUMN IF NOT EXISTS head_movement_count INTEGER"))



@app.get("/")
def root():
    return {
        "message": "HireSense AI backend is running"
    }


app.include_router(auth_router)
app.include_router(account_router)


def _warm_ollama_model() -> None:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": "Ready",
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": 1, "temperature": 0},
            },
            timeout=15,
        )
        response.raise_for_status()
        logger.info("Ollama model warm-up completed for %s", OLLAMA_MODEL)
    except requests.RequestException as exc:
        logger.warning("Ollama model warm-up failed for %s: %s", OLLAMA_MODEL, exc)


@app.on_event("startup")
def start_ollama_warmup() -> None:
    threading.Thread(target=_warm_ollama_model, daemon=True).start()


def _require_owned_session(session_id: UUID, user: User, db: Session) -> InterviewSession:
    session = db.scalar(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user.id,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session


def _run_analysis_background(session_id: UUID) -> None:
    db = SessionLocal()
    try:
        result = run_post_interview_analysis(db=db, session_id=session_id)
        insights = result.get("insights")
        analysis_status = (
            "failed"
            if isinstance(insights, dict) and insights.get("status") == "failed"
            else "completed"
        )
        db.execute(
            text(
                """
                UPDATE interview_insights
                SET analysis_status = :status,
                    insights_json = CAST(:insights AS jsonb),
                    timings_json = CAST(:timings AS jsonb),
                    error_message = :error,
                    updated_at = NOW()
                WHERE session_id = :session_id
                """
            ),
            {
                "session_id": session_id,
                "status": analysis_status,
                "insights": json.dumps(insights) if insights is not None else None,
                "timings": json.dumps(result.get("timings", {})),
                "error": insights.get("error") if isinstance(insights, dict) else None,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Post-interview analysis failed for session %s", session_id)
        db.execute(
            text(
                """
                UPDATE interview_insights
                SET analysis_status = 'failed', error_message = :error, updated_at = NOW()
                WHERE session_id = :session_id
                """
            ),
            {"session_id": session_id, "error": str(exc)[:1000]},
        )
        db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": result.scalar()
    }

@app.get("/job-profiles")
def get_job_profiles(
    db: Session = Depends(get_db),
):
    profiles = (
        db.query(JobProfile)
        .filter(JobProfile.is_active.is_(True))
        .order_by(JobProfile.title.asc())
        .all()
    )

    return [
        {
            "id": profile.id,
            "title": profile.title,
            "description": profile.description,
        }
        for profile in profiles
    ]

@app.post(
    "/interviews",
    response_model=SessionCreateResponse,
)
def create_interview(
    request: SessionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        session = create_interview_session(
            db=db,
            user_id=user.id,
            job_profile_id=request.job_profile_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    questions = [
        SessionQuestionResponse(
            id=question.id,
            question_order=question.question_order,
            question_text=question.question_text,
            source=question.source,
        )
        for question in session.questions
    ]

    return SessionCreateResponse(
        session_id=session.id,
        job_profile_id=session.job_profile_id,
        status=session.status,
        target_question_count=session.target_question_count,
        questions=questions,
    )



    
@app.get(
    "/interviews/{session_id}/current-question",
    response_model=SessionQuestionResponse,
)
def current_question(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_owned_session(session_id, user, db)
    try:
        question = get_current_question(
            db=db,
            session_id=session_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    return SessionQuestionResponse(
        id=question.id,
        question_order=question.question_order,
        question_text=question.question_text,
        source=question.source,
    )

 
@app.post(
    "/interviews/{session_id}/questions/{question_id}/answer",
    response_model=QuestionAnswerResponse,
)
def answer_question(
    session_id: UUID,
    question_id: UUID,
    transcript_text: str = Form(...),
    time_taken_seconds: int | None = Form(None),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_owned_session(session_id, user, db)
    try:
        session, answered_question, next_question = submit_question_answer(
            db=db,
            session_id=session_id,
            question_id=question_id,
            transcript_text=transcript_text,
            time_taken_seconds=time_taken_seconds,
            video_file=video,
        )
        if (
            not is_whisper_sync_enabled()
            and answered_question.video_url
        ):
            profile = session.job_profile
            enqueue_transcription(
                answered_question.id,
                answered_question.video_url,
                role=profile.title if profile else "",
                skills=list(profile.skills or []) if profile and profile.skills else [],
                question_text=answered_question.question_text,
            )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    next_question_response = None

    if next_question is not None:
        next_question_response = SessionQuestionResponse(
            id=next_question.id,
            question_order=next_question.question_order,
            question_text=next_question.question_text,
            source=next_question.source,
        )

    return QuestionAnswerResponse(
        session_id=session.id,
        answered_question_id=answered_question.id,
        status=session.status,
        next_question=next_question_response,
    )

 
@app.post("/interviews/{session_id}/video-analysis")
def analyze_interview_videos(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _require_owned_session(session_id, user, db)

    if session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=(
                "Post-interview analysis can only start "
                "after the interview is completed."
            ),
        )

    claimed = db.execute(
        text(
            """
            INSERT INTO interview_insights (session_id, analysis_status, started_at, updated_at)
            VALUES (:session_id, 'running', NOW(), NOW())
            ON CONFLICT (session_id) DO UPDATE
            SET analysis_status = 'running', insights_json = NULL, timings_json = NULL,
                error_message = NULL, started_at = NOW(), updated_at = NOW()
            WHERE interview_insights.analysis_status != 'running'
              AND (
                  interview_insights.analysis_status != 'completed'
                  OR EXISTS (
                      SELECT 1
                      FROM session_questions sq
                      LEFT JOIN nlp_evaluations nlp
                        ON nlp.session_question_id = sq.id
                      WHERE sq.session_id = :session_id
                        AND sq.answered_at IS NOT NULL
                        AND cardinality(
                            regexp_split_to_array(
                                NULLIF(
                                    trim(
                                        CASE
                                            WHEN sq.transcript_source = 'whisper'
                                                 AND sq.transcript_whisper IS NOT NULL
                                            THEN sq.transcript_whisper
                                            ELSE sq.transcript_text
                                        END
                                    ),
                                    ''
                                ),
                                '\\s+'
                            )
                        ) >= 5
                        AND (
                            (
                                sq.transcript_whisper IS NOT NULL
                                AND COALESCE(sq.transcript_source, 'browser') !=
                                    CASE
                                        WHEN sq.transcript_confidence
                                             < :whisper_confidence_fallback_threshold
                                        THEN 'browser'
                                        ELSE 'whisper'
                                    END
                            )
                            OR
                            nlp.session_question_id IS NULL
                            OR nlp.english_word_count IS NULL
                            OR nlp.code_switching_ratio IS NULL
                            OR nlp.language_switching_examples IS NULL
                            OR nlp.word_language_identification IS NULL
                        )
                  )
                  OR NOT COALESCE(
                      jsonb_typeof(
                          interview_insights.insights_json -> 'language_analysis'
                      ) = 'object',
                      FALSE
                  )
                  OR NOT COALESCE(
                      jsonb_typeof(
                          interview_insights.insights_json -> 'overall_scores'
                      ) = 'object',
                      FALSE
                  )
              )
            RETURNING analysis_status
            """
        ),
        {
            "session_id": session_id,
            "whisper_confidence_fallback_threshold": WHISPER_CONFIDENCE_FALLBACK_THRESHOLD,
        },
    ).scalar()
    db.commit()
    if claimed is None:
        current_status = db.execute(
            text("SELECT analysis_status FROM interview_insights WHERE session_id = :session_id"),
            {"session_id": session_id},
        ).scalar_one()
        return {"session_id": str(session_id), "analysis_status": current_status}

    background_tasks.add_task(_run_analysis_background, session_id)
    return {"session_id": str(session_id), "analysis_status": "running"}


@app.post("/interviews/{session_id}/language-analysis")
def analyze_interview_language(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _require_owned_session(session_id, user, db)
    if session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Language analysis can only run after the interview is completed.",
        )

    questions = db.scalars(
        select(SessionQuestion)
        .where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.answered_at.is_not(None),
        )
        .order_by(SessionQuestion.question_order)
    ).all()
    analyzed_questions = 0
    skipped_questions = 0
    report_refresh_required = False

    for question in questions:
        transcript, transcript_source = select_transcript(
            question.transcript_text,
            question.transcript_whisper,
            confidence=question.transcript_confidence,
        )
        if question.transcript_source != transcript_source:
            question.transcript_source = transcript_source
            question.audio_evaluation = None
            question.evaluation = None
            report_refresh_required = True
            db.commit()

        if (
            not is_transcript_usable(
                transcript,
                source=transcript_source,
                confidence=question.transcript_confidence,
            )
            or len(transcript.split()) < 5
        ):
            if question.nlp_evaluation is not None:
                question.nlp_evaluation = None
                report_refresh_required = True
            if (
                not is_transcript_usable(
                    transcript,
                    source=transcript_source,
                    confidence=question.transcript_confidence,
                )
                and question.evaluation is not None
            ):
                question.evaluation = None
                report_refresh_required = True
            db.commit()
            skipped_questions += 1
            continue
        try:
            analyze_session_question_nlp(db, question.id)
            analyzed_questions += 1
        except NLPAnalysisPipelineError:
            logger.exception(
                "Language analysis failed for question %s",
                question.id,
            )
            skipped_questions += 1

    evaluations = db.execute(
        text(
            """
            SELECT
                sq.question_order,
                nlp.word_count,
                nlp.hindi_word_count,
                nlp.english_word_count,
                nlp.dominant_language,
                nlp.code_switching_count,
                nlp.code_switching_ratio,
                nlp.hindi_words,
                nlp.english_words,
                nlp.language_switching_examples
            FROM session_questions sq
            JOIN nlp_evaluations nlp ON nlp.session_question_id = sq.id
            WHERE sq.session_id = :session_id
              AND sq.answered_at IS NOT NULL
            ORDER BY sq.question_order
            """
        ),
        {"session_id": session_id},
    ).mappings()

    question_results = []
    for evaluation in evaluations:
        nlp = dict(evaluation)
        for field, default in (
            ("hindi_words", {}),
            ("english_words", {}),
            ("language_switching_examples", []),
        ):
            try:
                nlp[field] = json.loads(nlp[field]) if nlp[field] else default
            except (TypeError, json.JSONDecodeError):
                logger.warning(
                    "Invalid %s data for language evaluation in session %s",
                    field,
                    session_id,
                )
                nlp[field] = default
        question_results.append({"nlp_evaluation": nlp})

    language_analysis = InsightAgent()._aggregate_language_analysis(
        question_results
    )
    db.execute(
        text(
            """
            INSERT INTO interview_insights (
                session_id, analysis_status, insights_json, started_at, updated_at
            )
            VALUES (
                :session_id,
                CASE
                    WHEN :report_refresh_required THEN 'pending'
                    ELSE 'completed'
                END,
                jsonb_build_object(
                    'status', 'ok',
                    'language_analysis', CAST(:language_analysis AS jsonb)
                ),
                NOW(),
                NOW()
            )
            ON CONFLICT (session_id) DO UPDATE
            SET insights_json = jsonb_set(
                    CASE
                        WHEN jsonb_typeof(interview_insights.insights_json) = 'object'
                        THEN interview_insights.insights_json
                        ELSE '{}'::jsonb
                    END,
                    '{language_analysis}',
                    CAST(:language_analysis AS jsonb),
                    TRUE
                ),
                analysis_status = CASE
                    WHEN interview_insights.analysis_status = 'running'
                    THEN 'running'
                    WHEN :report_refresh_required
                    THEN 'pending'
                    ELSE 'completed'
                END,
                updated_at = NOW()
            """
        ),
        {
            "session_id": session_id,
            "language_analysis": json.dumps(language_analysis, ensure_ascii=False),
            "report_refresh_required": report_refresh_required,
        },
    )
    db.commit()
    return {
        "session_id": str(session_id),
        "analysis_status": (
            "pending" if report_refresh_required else "completed"
        ),
        "analyzed_answers": language_analysis["analyzed_answer_count"],
        "code_switching_count": language_analysis["code_switching_count"],
        "feedback": language_analysis["feedback"],
        "processed_questions": analyzed_questions,
        "skipped_questions": skipped_questions,
    }


@app.get("/interviews/{session_id}/analysis-status")
def get_interview_analysis_status(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _require_owned_session(session_id, user, db)
    row = db.execute(
        text(
            """
            SELECT analysis_status, error_message, updated_at
            FROM interview_insights WHERE session_id = :session_id
            """
        ),
        {"session_id": session_id},
    ).mappings().first()
    analysis_status = (
        row["analysis_status"]
        if row
        else ("pending" if session.status == "completed" else "not_started")
    )
    return {
        "session_id": str(session_id),
        "analysis_status": analysis_status,
        "error": row["error_message"] if row else None,
        "updated_at": row["updated_at"].isoformat() if row and row["updated_at"] else None,
    }

@app.get("/interviews/{session_id}/analysis-results")
def get_interview_analysis_results(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Temporary developer-facing endpoint that returns all available
    evaluation data for an interview session.

    Includes:
    - answer_evaluations
    - audio_evaluations
    - nlp_evaluations
    - video_evaluations

    This endpoint is intended for the temporary analysis dashboard.
    """

    session = _require_owned_session(session_id, user, db)

    session_questions_result = db.execute(
        text(
            """
            SELECT
                id,
                question_order,
                question_text,
                source,
                source_question_id,
                parent_session_question_id,
                CASE
                    WHEN transcript_source = 'whisper' AND transcript_whisper IS NOT NULL
                    THEN transcript_whisper
                    ELSE transcript_text
                END AS transcript_text,
                COALESCE(transcript_source, 'browser') AS transcript_source,
                transcript_confidence,
                transcript_languages,
                time_taken_seconds,
                asked_at,
                answered_at
            FROM session_questions
            WHERE session_id = :session_id
              AND (answered_at IS NOT NULL OR transcript_text IS NOT NULL)
            ORDER BY question_order
            """
        ),
        {
            "session_id": session_id,
        },
    )

    session_questions = []

    for question_row in session_questions_result.mappings():
        question_id = question_row["id"]

        answer_result = db.execute(
            text(
                """
                SELECT row_to_json(t)
                FROM (
                    SELECT *
                    FROM answer_evaluations
                    WHERE session_question_id = :question_id
                    LIMIT 1
                ) t
                """
            ),
            {
                "question_id": question_id,
            },
        ).scalar()

        audio_result = db.execute(
            text(
                """
                SELECT row_to_json(t)
                FROM (
                    SELECT *
                    FROM audio_evaluations
                    WHERE session_question_id = :question_id
                    LIMIT 1
                ) t
                """
            ),
            {
                "question_id": question_id,
            },
        ).scalar()

        nlp_result = db.execute(
            text(
                """
                SELECT row_to_json(t)
                FROM (
                    SELECT *
                    FROM nlp_evaluations
                    WHERE session_question_id = :question_id
                    LIMIT 1
                ) t
                """
            ),
            {
                "question_id": question_id,
            },
        ).scalar()

        video_result = db.execute(
            text(
                """
                SELECT row_to_json(t)
                FROM (
                    SELECT *
                    FROM video_evaluations
                    WHERE session_question_id = :question_id
                    LIMIT 1
                ) t
                """
            ),
            {
                "question_id": question_id,
            },
        ).scalar()

        question_data = dict(question_row)

        question_data["answer_evaluation"] = answer_result
        question_data["audio_evaluation"] = audio_result
        question_data["nlp_evaluation"] = nlp_result
        question_data["video_evaluation"] = video_result
        try:
            question_data["transcript_languages"] = json.loads(
                question_data["transcript_languages"] or "[]"
            )
        except (TypeError, json.JSONDecodeError):
            logger.warning(
                "Invalid transcript language metadata for question %s",
                question_id,
            )
            question_data["transcript_languages"] = []

        session_questions.append(question_data)

    cached = db.execute(
        text(
            """
            SELECT analysis_status, insights_json, timings_json, error_message
            FROM interview_insights WHERE session_id = :session_id
            """
        ),
        {"session_id": session_id},
    ).mappings().first()
    language_metrics_stale = db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM session_questions sq
                LEFT JOIN nlp_evaluations nlp
                  ON nlp.session_question_id = sq.id
                WHERE sq.session_id = :session_id
                  AND sq.answered_at IS NOT NULL
                  AND cardinality(
                      regexp_split_to_array(
                          NULLIF(
                              trim(
                                  CASE
                                      WHEN sq.transcript_source = 'whisper'
                                           AND sq.transcript_whisper IS NOT NULL
                                      THEN sq.transcript_whisper
                                      ELSE sq.transcript_text
                                  END
                              ),
                              ''
                          ),
                          '\\s+'
                      )
                  ) >= 5
                  AND (
                      (
                          sq.transcript_whisper IS NOT NULL
                          AND COALESCE(sq.transcript_source, 'browser') !=
                              CASE
                                  WHEN sq.transcript_confidence
                                       < :whisper_confidence_fallback_threshold
                                  THEN 'browser'
                                  ELSE 'whisper'
                              END
                      )
                      OR
                      nlp.session_question_id IS NULL
                      OR nlp.english_word_count IS NULL
                      OR nlp.code_switching_ratio IS NULL
                      OR nlp.language_switching_examples IS NULL
                      OR nlp.word_language_identification IS NULL
                  )
            )
            """
        ),
        {
            "session_id": session_id,
            "whisper_confidence_fallback_threshold": WHISPER_CONFIDENCE_FALLBACK_THRESHOLD,
        },
    ).scalar()
    language_report = (
        cached["insights_json"].get("language_analysis")
        if cached and isinstance(cached["insights_json"], dict)
        else None
    )
    language_report_stale = not isinstance(language_report, dict)
    full_report = (
        cached["insights_json"]
        if cached and isinstance(cached["insights_json"], dict)
        else None
    )
    full_report_stale = (
        not isinstance(full_report, dict)
        or not isinstance(full_report.get("overall_scores"), dict)
    )
    analysis_status = (
        "pending"
        if cached
        and cached["analysis_status"] == "completed"
        and (
            language_metrics_stale
            or language_report_stale
            or full_report_stale
        )
        else cached["analysis_status"] if cached else "pending"
    )

    return {
        "session": {
            "id": str(session.id),
            "status": session.status,
            "target_question_count": session.target_question_count,
            "started_at": (
                session.started_at.isoformat()
                if session.started_at
                else None
            ),
            "ended_at": (
                session.ended_at.isoformat()
                if session.ended_at
                else None
            ),
        },
        "questions": session_questions,
        "insights": cached["insights_json"] if cached else None,
        "analysis_status": analysis_status,
        "analysis_timings": cached["timings_json"] if cached else None,
        "analysis_error": cached["error_message"] if cached else None,
    }


@app.post("/interviews/{session_id}/report")
def save_interview_report(
    session_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Save the candidate's interview feedback report and/or generated PDF
    associated with the session ID.
    """
    _require_owned_session(session_id, user, db)

    report_json = payload.get("report_json")
    pdf_data = payload.get("pdf_data")

    db.execute(
        text(
            """
            INSERT INTO interview_reports (session_id, report_json, pdf_data)
            VALUES (:session_id, :report_json, :pdf_data)
            """
        ),
        {
            "session_id": session_id,
            "report_json": json.dumps(report_json) if report_json else None,
            "pdf_data": pdf_data,
        },
    )
    db.commit()

    return {
        "status": "saved",
        "session_id": str(session_id),
    }


@app.get("/interviews/{session_id}/report")
def get_interview_report(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retrieve the saved candidate report and/or PDF for an interview session.
    """
    _require_owned_session(session_id, user, db)
    row = db.execute(
        text(
            """
            SELECT id, session_id, report_json, pdf_data, created_at
            FROM interview_reports
            WHERE session_id = :session_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"session_id": session_id},
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Saved report not found for this session.",
        )

    return {
        "id": str(row["id"]),
        "session_id": str(row["session_id"]),
        "report_json": row["report_json"],
        "pdf_data": row["pdf_data"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }