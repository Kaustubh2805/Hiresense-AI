from __future__ import annotations

from app.agents.agent_decision import AgentAction, AgentDecision
from app.agents.interview_state import InterviewState


MAX_FOLLOWUPS_PER_INTERVIEW = 5


class InterviewAgent:
    """
    Decision layer for adaptive interview behavior.

    The technical evaluator measures the candidate's answer.
    This agent interprets that result together with the current
    interview state and decides what should happen next.

    The agent does not:
    - modify the database
    - calculate the technical evaluation
    - generate the actual question
    - execute analysis pipelines

    Those responsibilities remain with the existing services.
    """

    def decide(self, state: InterviewState) -> AgentDecision:
        """
        Decide what should happen after the current answer.

        The decision uses:
        - the current technical evaluation
        - whether the current answer needs a follow-up
        - follow-ups already used
        - recent technical performance
        - previous interview history
        - the current question context
        - the remaining question budget

        Decision priority:

        1. If the current answer requires a follow-up, resolve it first.
        2. Respect the global follow-up limit.
        3. If technical evaluation is unavailable, continue safely.
        4. If the question budget has been reached, finish.
        5. If the evaluator identifies a weakness, probe it.
        6. Otherwise continue to the next question.
        """

        # ---------------------------------------------------------
        # 1. READ RECENT INTERVIEW PERFORMANCE
        # ---------------------------------------------------------

        recent_scores = self._get_recent_scores(
            state,
            limit=3,
        )

        declining_performance = self._is_declining(
            recent_scores
        )

        repeated_weakness = self._has_repeated_weakness(
            state
        )

        # ---------------------------------------------------------
        # 2. FOLLOW-UP LIMIT
        # ---------------------------------------------------------
        #
        # A follow-up is only considered when the current answer
        # actually requires one.
        #
        # Once the global follow-up limit is reached, the agent
        # must not request another follow-up.
        # ---------------------------------------------------------

        if (
            state.needs_followup
            and state.followups_used >= MAX_FOLLOWUPS_PER_INTERVIEW
        ):
            return self._finish_or_continue(
                state=state,
                reason=(
                    "The current answer requires additional probing, "
                    "but the maximum number of interview follow-ups "
                    "has been reached."
                ),
            )

        # ---------------------------------------------------------
        # 3. NO TECHNICAL EVALUATION
        # ---------------------------------------------------------
        #
        # We cannot make a meaningful adaptive decision without
        # the evaluator result.
        #
        # If the interview budget has already been reached, however,
        # the interview should still finish.
        # ---------------------------------------------------------

        if state.technical_score is None:
            return self._finish_or_continue(
                state=state,
                reason=(
                    "No technical evaluation is available for the "
                    "current answer."
                ),
            )

        # ---------------------------------------------------------
        # 4. ADAPTIVE FOLLOW-UP
        # ---------------------------------------------------------
        #
        # The evaluator's current needs_followup signal remains
        # authoritative.
        #
        # Historical state is used only to make the follow-up
        # instruction more targeted.
        # ---------------------------------------------------------

        if state.needs_followup:

            # -----------------------------------------------------
            # 4A. MULTIPLE PREVIOUS FOLLOW-UPS
            # -----------------------------------------------------

            if state.followups_used >= 3:
                instruction = (
                    "Ask one concise, highly targeted follow-up "
                    "focused only on the most important weakness "
                    "in the candidate's current answer. Do not "
                    "broaden the topic."
                )

                if repeated_weakness:
                    instruction += (
                        " The candidate has shown a repeated weakness "
                        "in recent answers, so use the follow-up to "
                        "test that specific area directly."
                    )

                return AgentDecision(
                    action=AgentAction.ASK_FOLLOWUP,
                    reason=(
                        "The current answer still requires clarification "
                        "according to the technical evaluation, and the "
                        "interview history indicates that the follow-up "
                        "should remain narrowly focused."
                    ),
                    confidence=0.8,
                    followup_instruction=instruction,
                )

            # -----------------------------------------------------
            # 4B. CURRENT WEAKNESS + DECLINING PERFORMANCE
            # -----------------------------------------------------

            if declining_performance:
                return AgentDecision(
                    action=AgentAction.ASK_FOLLOWUP,
                    reason=(
                        "The current answer requires additional probing, "
                        "and recent technical performance is declining. "
                        "The agent should use the current topic to clarify "
                        "the candidate's understanding before progressing."
                    ),
                    confidence=0.9,
                    followup_instruction=(
                        "The candidate's recent performance is declining. "
                        "Probe the current weak area with a focused question that "
                        "checks whether the candidate understands the underlying concept."
                    ),
                )

            # -----------------------------------------------------
            # 4C. CURRENT WEAKNESS + REPEATED WEAK AREA
            # -----------------------------------------------------

            if repeated_weakness:
                return AgentDecision(
                    action=AgentAction.ASK_FOLLOWUP,
                    reason=(
                        "The current answer requires additional probing "
                        "and the interview history indicates a repeated "
                        "weakness that should be examined further."
                    ),
                    confidence=0.9,
                    followup_instruction=(
                        "The candidate has shown a repeated weakness. "
                        "Probe that weakness directly using a focused technical question. "
                        "Prefer a concrete example or practical scenario."
                    ),
                )

            # -----------------------------------------------------
            # 4D. NORMAL FOLLOW-UP
            # -----------------------------------------------------

            return AgentDecision(
                action=AgentAction.ASK_FOLLOWUP,
                reason=(
                    "The current answer contains a weakness that "
                    "requires additional probing before moving to "
                    "the next topic."
                ),
                confidence=0.9,
                followup_instruction=(
                    "Probe the candidate's weak area from the current answer. "
                    "Ask for clarification or a concrete technical explanation "
                    "of the missing concept."
                ),
            )

        # ---------------------------------------------------------
        # 5. QUESTION BUDGET
        # ---------------------------------------------------------
        #
        # The current answer does NOT need a follow-up.
        #
        # Now the agent can decide whether another question is
        # allowed.
        #
        # We intentionally check this AFTER follow-up handling so
        # that a question at the budget boundary can still receive
        # one necessary follow-up.
        # ---------------------------------------------------------

        if self._question_budget_reached(state):
            return AgentDecision(
                action=AgentAction.FINISH,
                reason=(
                    "The interview question budget has been reached, "
                    "and the current answer does not require another "
                    "follow-up. The interview should finish."
                ),
                confidence=1.0,
            )

        # ---------------------------------------------------------
        # 6. NORMAL PROGRESSION
        # ---------------------------------------------------------

        if declining_performance:
            return AgentDecision(
                action=AgentAction.ASK_NEXT_QUESTION,
                reason=(
                    "The current answer does not require additional "
                    "probing according to the technical evaluation. "
                    "Although recent performance has declined, the "
                    "current topic can be completed and the interview "
                    "should continue to the next question."
                ),
                confidence=0.85,
            )

        if repeated_weakness:
            return AgentDecision(
                action=AgentAction.ASK_NEXT_QUESTION,
                reason=(
                    "The current answer does not require additional "
                    "probing according to the technical evaluation. "
                    "The interview history contains a repeated weak "
                    "area, but the current answer does not require "
                    "another follow-up."
                ),
                confidence=0.85,
            )

        return AgentDecision(
            action=AgentAction.ASK_NEXT_QUESTION,
            reason=(
                "The candidate's current answer does not require "
                "additional probing, so the interview should move "
                "to the next question."
            ),
            confidence=0.9,
        )

    # =============================================================
    # INTERNAL DECISION HELPERS
    # =============================================================

    @staticmethod
    def _question_budget_reached(
        state: InterviewState,
    ) -> bool:
        """
        Determine whether the configured interview question budget
        has been reached.

        A missing budget means there is no explicit budget constraint.
        """

        if state.question_budget is None:
            return False

        return state.questions_asked >= state.question_budget

    def _finish_or_continue(
        self,
        state: InterviewState,
        reason: str,
    ) -> AgentDecision:
        """
        Safely decide whether to finish or continue when the normal
        adaptive path cannot be used.

        If a question budget exists and has been reached, finish.
        Otherwise continue with the next question.
        """

        if self._question_budget_reached(state):
            return AgentDecision(
                action=AgentAction.FINISH,
                reason=(
                    f"{reason} The interview question budget has "
                    "also been reached, so the interview should finish."
                ),
                confidence=1.0,
            )

        return AgentDecision(
            action=AgentAction.ASK_NEXT_QUESTION,
            reason=(
                f"{reason} The interview budget has not been reached, "
                "so the interview should continue with the next question."
            ),
            confidence=0.8,
        )

    # =============================================================
    # INTERNAL STATE HELPERS
    # =============================================================

    @staticmethod
    def _get_recent_scores(
        state: InterviewState,
        limit: int = 3,
    ) -> list[float]:
        """
        Return the most recent available technical scores.

        The current score is already present in technical_scores
        because interview_service.py adds the current evaluation
        while constructing InterviewState.

        No new scoring or normalization is performed here.
        """

        scores = [
            float(score)
            for score in state.technical_scores
            if score is not None
        ]

        if not scores:
            return []

        return scores[-limit:]

    @staticmethod
    def _is_declining(
        scores: list[float],
    ) -> bool:
        """
        Detect a simple downward trend in recent performance.

        Examples:

            [8, 7, 5] -> True
            [5, 7, 8] -> False
            [8, 8, 7] -> False
            [5, 4]    -> True
        """

        if len(scores) < 2:
            return False

        return all(
            scores[index] < scores[index - 1]
            for index in range(1, len(scores))
        )

    @staticmethod
    def _has_repeated_weakness(
        state: InterviewState,
    ) -> bool:
        """
        Detect whether the interview history contains repeated
        weakness information.

        This currently uses exact weakness descriptions because
        InterviewState does not yet contain a structured weakness
        taxonomy.
        """

        weaknesses = [
            str(weakness).strip().lower()
            for weakness in state.recent_weaknesses
            if str(weakness).strip()
        ]

        if len(weaknesses) < 2:
            return False

        return len(set(weaknesses)) < len(weaknesses)