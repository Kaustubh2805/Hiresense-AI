
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/components/auth-guard";
import { Badge, ProgressRing } from "@/components/ui";
import { apiFetch } from "@/lib/api";

function getCurrentTimestamp() {
  return Date.now();
}

type JobProfile = {
  id: string;
  title: string;
  description: string | null;
  match_percent?: number | null;
  matched_skills?: string[];
  missing_skills?: string[];
  recommended?: boolean;
  recommended_rank?: number | null;
  badge?: "Best match" | "Also a good fit" | null;
  reason?: string;
};

type Question = {
  id: string;
  question_order: number;
  question_text: string;
  source: string;
};

type InterviewSession = {
  session_id: string;
  job_profile_id: string;
  status: string;
  target_question_count: number;
  questions: Question[];
};

type QuestionAnswerResponse = {
  session_id: string;
  answered_question_id: string;
  status: string;
  next_question: Question | null;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
      isFinal: boolean;
    };
  };
};

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;

  onresult:
    | ((event: SpeechRecognitionEventLike) => void)
    | null;

  onerror:
    | ((event: { error: string }) => void)
    | null;

  onend: (() => void) | null;

  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor =
  new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

function InterviewFlow() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<JobProfile[]>([]);
  const [resumeRequired, setResumeRequired] = useState(false);
  const [recommendationWarning, setRecommendationWarning] = useState(false);
  const [recommendationMessage, setRecommendationMessage] = useState("");
  const [selectedProfile, setSelectedProfile] =
    useState<JobProfile | null>(null);

  const [loadingProfiles, setLoadingProfiles] =
    useState(true);

  const [startingInterview, setStartingInterview] =
    useState(false);

  const [error, setError] = useState("");

  const [session, setSession] =
    useState<InterviewSession | null>(null);

  const [currentQuestion, setCurrentQuestion] =
    useState<Question | null>(null);

  const [mediaReady, setMediaReady] =
    useState(false);
  const [readinessOpen, setReadinessOpen] = useState(false);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [readinessError, setReadinessError] = useState("");
  const [microphoneLevel, setMicrophoneLevel] = useState(0);
  const [readinessChecks, setReadinessChecks] = useState<string[]>([]);

  const [isRecording, setIsRecording] =
    useState(false);

  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const [lockedQuestionIds, setLockedQuestionIds] =
    useState<Set<string>>(new Set());

  const [recordingSeconds, setRecordingSeconds] =
    useState(0);

  const [transcript, setTranscript] =
    useState("");

  const [interviewComplete, setInterviewComplete] =
    useState(false);
  const [restoredSessionId, setRestoredSessionId] = useState<string | null>(null);

  const [postAnalysisLoading, setPostAnalysisLoading] =
  useState(false);

  const [submissionFailed, setSubmissionFailed] =
    useState(false);



  const videoRef =
    useRef<HTMLVideoElement | null>(null);
  const readinessVideoRef = useRef<HTMLVideoElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const microphoneAnimationRef = useRef<number | null>(null);

  const mediaStreamRef =
    useRef<MediaStream | null>(null);

  const mediaRecorderRef =
    useRef<MediaRecorder | null>(null);

  const recordedChunksRef =
    useRef<Blob[]>([]);

  const recordingStartedAtRef =
    useRef<number | null>(null);

  const timerRef =
    useRef<ReturnType<typeof setInterval> | null>(null);

  const recognitionRef =
    useRef<SpeechRecognitionLike | null>(null);

  const transcriptRef =
    useRef("");

  const finalizedTranscriptRef = useRef("");
  const interimTranscriptRef = useRef("");
  const shouldListenRef = useRef(false);
  const recognitionRestartTimerRef =
    useRef<ReturnType<typeof setTimeout> | null>(null);
  const recognitionRestartAttemptsRef = useRef(0);

  /*
   * Prevent duplicate POST requests while a submission
   * is already being processed.
   */
  const submitInProgressRef =
    useRef(false);

  /*
   * Keep the question being recorded stable.
   *
   * This prevents a React state update from accidentally
   * changing the question ID while a recording is being
   * submitted.
   */
  const recordingQuestionRef =
    useRef<Question | null>(null);

  /*
   * Keep track of questions whose submissions have already
   * been accepted/are currently being submitted.
   */
  const submittedQuestionIdsRef =
    useRef<Set<string>>(new Set());

  /*
   * Lock the question immediately when recording is stopped.
   */
  const stoppingQuestionIdRef =
    useRef<string | null>(null);

  /*
   * Restore completion state if the page is unexpectedly
   * reloaded after the final answer.
   *
   * This is stored only for the current browser tab/session.
   */
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("hiresense_interview_complete");
      if (stored) {
        const completion = JSON.parse(stored) as {
          sessionId?: unknown;
          completed?: unknown;
        };
        const sessionId = completion.sessionId;
        if (
          completion.completed === true
          && typeof sessionId === "string"
        ) {
          queueMicrotask(() => {
            setRestoredSessionId(sessionId);
            setInterviewComplete(true);
          });
        }

      }
    } catch (err) {
      console.warn(
        "[browser] Could not restore completion state:",
        err,
      );
    }
  }, []);

  useEffect(() => {
    const stream = mediaStreamRef.current;
    if (!stream) return;
    if (readinessOpen && !session && readinessVideoRef.current) {
      readinessVideoRef.current.srcObject = stream;
    }
    if (session && videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  }, [readinessOpen, session, mediaReady]);

  /*
   * Load job profiles
   */
  useEffect(() => {
    async function loadProfiles() {
      try {
        setLoadingProfiles(true);
        setError("");
        setRecommendationWarning(false);
        setRecommendationMessage("");

        const response = await apiFetch("/job-profiles");

        if (!response.ok) {
          const message =
            await response.text();

          throw new Error(
            message ||
              "Failed to load job profiles.",
          );
        }

        const data: JobProfile[] = await response.json();
        setProfiles(data);
        setSelectedProfile(data[0] ?? null);
        try {
          const recommendationResponse = await apiFetch("/me/recommended-job-profiles");
          if (!recommendationResponse.ok) {
            throw new Error("Could not load your role recommendations.");
          }
          const recommendationData: {
            resume_required?: boolean;
            message?: string;
            profiles?: JobProfile[];
          } = await recommendationResponse.json();
          setResumeRequired(Boolean(recommendationData.resume_required));
          setRecommendationMessage(recommendationData.message || "");
          const recommendations = new Map<string, JobProfile>(
            (recommendationData.profiles || []).map((profile) => [profile.id, profile]),
          );
          const ordered = data
            .map((profile) => ({ ...profile, ...recommendations.get(profile.id) }))
            .sort((a, b) =>
              (a.recommended_rank ?? Number.MAX_SAFE_INTEGER)
                - (b.recommended_rank ?? Number.MAX_SAFE_INTEGER)
              || (b.match_percent ?? 0) - (a.match_percent ?? 0)
              || a.title.localeCompare(b.title),
            );
          setProfiles(ordered);
          setSelectedProfile(
            ordered.find((profile) => profile.recommended_rank === 1)
              ?? ordered[0]
              ?? null,
          );
        } catch (recommendationError) {
          console.warn(
            "[browser] Could not load role recommendations:",
            recommendationError,
          );
          setRecommendationWarning(true);
        }
      } catch (err) {
        console.error(
          "[browser] Load profiles error:",
          err,
        );

        setError(
          "Unable to connect to HireSense backend. Make sure the backend is running.",
        );
      } finally {
        setLoadingProfiles(false);
      }
    }

    loadProfiles();
  }, []);

  /*
   * Speak current question
   */
  useEffect(() => {
    if (!currentQuestion || !session || interviewComplete) {
      return;
    }

    if (
      typeof window === "undefined" ||
      !("speechSynthesis" in window)
    ) {
      return;
    }

    window.speechSynthesis.cancel();

    const utterance =
      new SpeechSynthesisUtterance(
        currentQuestion.question_text,
      );

    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(
      utterance,
    );

    return () => {
      window.speechSynthesis.cancel();
    };
  }, [
    currentQuestion,
    session,
    interviewComplete,
  ]);

  /*
   * Start interview
   */
  async function startInterview() {
    return prepareInterview(selectedProfile);
  }

  function stopMicrophoneMeter() {
    if (microphoneAnimationRef.current !== null) {
      cancelAnimationFrame(microphoneAnimationRef.current);
      microphoneAnimationRef.current = null;
    }
    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
  }

  async function prepareInterview(profile: JobProfile | null) {
    if (!profile || startingInterview || readinessLoading) return;
    setSelectedProfile(profile);
    setReadinessOpen(true);
    setReadinessLoading(true);
    setError("");
    setReadinessError("");
    setReadinessChecks([]);
    stopMicrophoneMeter();

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera and microphone access are not supported by this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      mediaStreamRef.current = stream;
      setMediaReady(true);

      try {
        const audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        audioContext.createMediaStreamSource(stream).connect(analyser);
        audioContextRef.current = audioContext;
        const samples = new Uint8Array(analyser.fftSize);
        const measureLevel = () => {
          analyser.getByteTimeDomainData(samples);
          const rms = Math.sqrt(
            samples.reduce((sum, sample) => sum + (sample - 128) ** 2, 0)
              / samples.length,
          ) / 128;
          setMicrophoneLevel(Math.min(100, Math.round(rms * 500)));
          microphoneAnimationRef.current = requestAnimationFrame(measureLevel);
        };
        void audioContext.resume().then(() => {
          if (audioContextRef.current === audioContext) {
            measureLevel();
          }
        }).catch((meterError: unknown) => {
          console.warn("[browser] Could not start microphone level monitoring:", meterError);
        });
      } catch (meterError) {
        console.warn("[browser] Microphone level meter is unavailable:", meterError);
      }
    } catch (err) {
      console.error("[browser] Camera/microphone readiness check failed:", err);
      setMediaReady(false);
      setReadinessError(
        err instanceof Error
          ? `${err.message} Allow camera and microphone access in your browser settings, then try again.`
          : "Camera or microphone access failed. Check your browser permissions and try again.",
      );
    } finally {
      setReadinessLoading(false);
    }
  }

  function cancelReadiness() {
    stopMicrophoneMeter();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    setMediaReady(false);
    setMicrophoneLevel(0);
    setReadinessChecks([]);
    setReadinessError("");
    setReadinessOpen(false);
  }

  function toggleReadinessCheck(check: string) {
    setReadinessChecks((current) =>
      current.includes(check)
        ? current.filter((item) => item !== check)
        : [...current, check],
    );
  }

  async function startInterviewForProfile(profile: JobProfile | null) {
    if (!profile || startingInterview) {
      return;
    }

    try {
      setStartingInterview(true);
      setError("");
      setSubmissionFailed(false);
      setInterviewComplete(false);

      /*
       * A new interview is a completely new submission
       * lifecycle.
       */
      submittedQuestionIdsRef.current.clear();
      stoppingQuestionIdRef.current = null;
      setLockedQuestionIds(new Set());
      submitInProgressRef.current = false;

      /*
       * Remove the previous completion flag.
       */
      try {
        sessionStorage.removeItem(
          "hiresense_interview_complete",
        );
      } catch (storageError) {
        console.warn("[browser] Could not clear completion state:", storageError);
      }
      setRestoredSessionId(null);

      const response = await apiFetch(
        "/interviews",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            job_profile_id: profile.id,
          }),
        },
      );

      const rawResponse =
        await response.text();

      let data: unknown = null;

      try {
        data = rawResponse
          ? JSON.parse(rawResponse)
          : null;
      } catch {
        data = rawResponse;
      }

      if (!response.ok) {
        console.error(
          "[browser] Start interview response:",
          {
            status: response.status,
            statusText:
              response.statusText,
            data,
          },
        );

        let message =
          "Failed to start interview.";

        if (
          typeof data === "object" &&
          data !== null &&
          "detail" in data
        ) {
          message = String(
            (data as { detail: unknown }).detail,
          );
        } else if (
          typeof data === "string" &&
          data.trim()
        ) {
          message = data;
        }

        throw new Error(message);
      }

      const interviewData =
        data as InterviewSession;

      if (
        !interviewData.session_id ||
        !interviewData.questions ||
        interviewData.questions.length === 0
      ) {
        throw new Error(
          "The backend started the interview but did not return a question.",
        );
      }

      stopMicrophoneMeter();
      setReadinessOpen(false);
      setSession(interviewData);

      setCurrentQuestion(
        interviewData.questions[0],
      );

      setTranscript("");
      transcriptRef.current = "";

      setInterviewComplete(false);
      setSubmissionFailed(false);

      await startCamera();
    } catch (err) {
      console.error(
        "[browser] Start interview error:",
        err,
      );

      const message =
        err instanceof Error
          ? err.message
          : "Unknown error";

      setError(
        `Unable to start the interview: ${message}`,
      );
    } finally {
      setStartingInterview(false);
    }
  }

  function navigateHome() {
    try {
      sessionStorage.removeItem("hiresense_interview_complete");
    } catch (storageError) {
      console.warn("[browser] Could not clear completion state:", storageError);
    }
    router.push("/");
  }

  /*
   * Start camera + microphone
   */
  async function startCamera() {
    try {
      setError("");

      if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
      ) {
        throw new Error(
          "Media devices are not supported by this browser.",
        );
      }

      const stream = mediaStreamRef.current
        ?? await navigator.mediaDevices.getUserMedia(
          {
            video: true,
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
              channelCount: 1,
            },
          },
        );

      mediaStreamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject =
          stream;
      }

      setMediaReady(true);
    } catch (err) {
      console.error(
        "[browser] Camera/microphone error:",
        err,
      );

      setMediaReady(false);

      setError(
        "Camera or microphone permission was denied. Please allow camera and microphone access in your browser.",
      );
    }
  }

  /*
   * Start browser speech recognition
   */
  function startSpeechRecognition() {
    if (typeof window === "undefined") {
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn(
        "[Speech] Speech recognition is not supported in this browser.",
      );

      return;
    }

    const recognition =
      new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-IN";

    recognition.onresult = (
      event: SpeechRecognitionEventLike,
    ) => {
      let finalizedPart = "";
      let interim = "";

      for (
        let i = event.resultIndex;
        i < event.results.length;
        i++
      ) {
        const result = event.results[i];
        const resultText = result[0].transcript.trim();
        if (!resultText) continue;
        if (result.isFinal) {
          finalizedPart += `${resultText} `;
        } else {
          interim += `${resultText} `;
        }
      }

      if (finalizedPart) {
        finalizedTranscriptRef.current = [
          finalizedTranscriptRef.current,
          finalizedPart.trim(),
        ].filter(Boolean).join(" ");
      }
      interimTranscriptRef.current = interim.trim();
      recognitionRestartAttemptsRef.current = 0;
      const liveTranscript = [
        finalizedTranscriptRef.current,
        interimTranscriptRef.current,
      ].filter(Boolean).join(" ");
      transcriptRef.current = liveTranscript;
      setTranscript(liveTranscript);
    };

    recognition.onerror = (event) => {
      console.warn(
        "[Speech] Speech recognition error:",
        event.error,
      );
      if (event.error === "not-allowed") {
        shouldListenRef.current = false;
        setError(
          "Live transcription permission was blocked. Allow microphone access for this site in your browser settings, then start recording again. Your video recording can still be submitted.",
        );
      } else if (
        event.error === "network" ||
        event.error === "no-speech" ||
        event.error === "aborted"
      ) {
        recognitionRestartAttemptsRef.current += 1;
      }
    };

    recognition.onend = () => {
      if (!shouldListenRef.current) return;
      if (recognitionRestartTimerRef.current) {
        clearTimeout(recognitionRestartTimerRef.current);
      }
      if (recognitionRestartAttemptsRef.current >= 5) {
        shouldListenRef.current = false;
        console.info(
          "[Speech] Live transcription paused after repeated restart failures; the recording will still be transcribed on the server.",
        );
        return;
      }
      recognitionRestartTimerRef.current = setTimeout(() => {
        if (!shouldListenRef.current || recognitionRef.current !== recognition) {
          return;
        }
        try {
          recognition.start();
        } catch (err) {
          recognitionRestartAttemptsRef.current += 1;
          console.warn("[Speech] Recognition restart failed:", err);
        }
      }, 250);
    };

    recognitionRef.current =
      recognition;

    try {
      recognition.start();
    } catch (err) {
      recognitionRestartAttemptsRef.current += 1;
      console.warn(
        "[Speech] Could not start recognition:",
        err,
      );
    }
  }

  /*
   * Start video recording
   */
  function startRecording() {
    if (interviewComplete) {
      return;
    }

    if (!mediaStreamRef.current) {
      setError(
        "Camera is not ready yet.",
      );

      return;
    }

    if (!window.MediaRecorder) {
      setError(
        "Your browser does not support video recording.",
      );

      return;
    }

    if (isSubmitting) {
      return;
    }

    if (
      submitInProgressRef.current
    ) {
      return;
    }

    if (!session || !currentQuestion) {
      setError(
        "Interview question is not available.",
      );

      return;
    }

    /*
     * Do not allow a question that is already being
     * stopped/submitted to start another recording.
     */
    if (
      stoppingQuestionIdRef.current ===
      currentQuestion.id
    ) {
      console.warn(
        "[browser] Recording already stopping for this question.",
      );

      return;
    }

    /*
     * Do not allow the same question to be submitted
     * again after it has already been accepted.
     */
    if (
      submittedQuestionIdsRef.current.has(
        currentQuestion.id,
      )
    ) {
      console.warn(
        "[browser] Question already submitted:",
        currentQuestion.id,
      );

      return;
    }

    try {
      setError("");
      setSubmissionFailed(false);

      recordedChunksRef.current = [];

      /*
       * Remember exactly which question this
       * recording belongs to.
       */
      recordingQuestionRef.current =
        currentQuestion;

      stoppingQuestionIdRef.current =
        null;

      let mimeType = "";

      if (
        MediaRecorder.isTypeSupported(
          "video/webm;codecs=vp9,opus",
        )
      ) {
        mimeType =
          "video/webm;codecs=vp9,opus";
      } else if (
        MediaRecorder.isTypeSupported(
          "video/webm;codecs=vp8,opus",
        )
      ) {
        mimeType =
          "video/webm;codecs=vp8,opus";
      } else if (
        MediaRecorder.isTypeSupported(
          "video/webm",
        )
      ) {
        mimeType = "video/webm";
      }

      const recorder = mimeType
        ? new MediaRecorder(
            mediaStreamRef.current,
            { mimeType, audioBitsPerSecond: 128000 },
          )
        : new MediaRecorder(
            mediaStreamRef.current,
            { audioBitsPerSecond: 128000 },
          );

      recorder.ondataavailable = (
        event,
      ) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(
            event.data,
          );
        }
      };

      recorder.onstop = () => {
        /*
         * MediaRecorder's stop event happens after
         * the final dataavailable event.
         */
        void submitRecording();
      };

      mediaRecorderRef.current =
        recorder;

      recordingStartedAtRef.current =
        getCurrentTimestamp();

      setRecordingSeconds(0);

      setTranscript("");
      transcriptRef.current = "";
      finalizedTranscriptRef.current = "";
      interimTranscriptRef.current = "";
      shouldListenRef.current = true;
      recognitionRestartAttemptsRef.current = 0;

      if (timerRef.current) {
        clearInterval(
          timerRef.current,
        );
      }

      timerRef.current =
        setInterval(() => {
          if (
            recordingStartedAtRef.current
          ) {
            const elapsed =
              Math.floor(
                (getCurrentTimestamp() -
                  recordingStartedAtRef.current) /
                  1000,
              );

            setRecordingSeconds(
              elapsed,
            );
          }
        }, 1000);

      recorder.start(1000);

      setIsRecording(true);

      startSpeechRecognition();
    } catch (err) {
      console.error(
        "[browser] Start recording error:",
        err,
      );

      setError(
        "Unable to start recording.",
      );
    }
  }

  /*
   * Stop recording
   */
  function stopRecording() {
    if (interviewComplete) {
      return;
    }

    const recorder =
      mediaRecorderRef.current;

    if (!recorder) {
      return;
    }

    const question =
      recordingQuestionRef.current;

    /*
     * Lock this question BEFORE calling recorder.stop().
     */
    if (question) {
      stoppingQuestionIdRef.current =
        question.id;
      setLockedQuestionIds((current) => new Set(current).add(question.id));
    }

    /*
     * Immediately mark submission as pending.
     */
    submitInProgressRef.current = true;
    setIsSubmitting(true);
    shouldListenRef.current = false;

    if (recognitionRestartTimerRef.current) {
      clearTimeout(recognitionRestartTimerRef.current);
      recognitionRestartTimerRef.current = null;
    }

    const transcriptAtStop = [
      finalizedTranscriptRef.current,
      interimTranscriptRef.current,
    ].filter(Boolean).join(" ").trim();
    transcriptRef.current = transcriptAtStop;
    setTranscript(transcriptAtStop);

    if (
      recorder.state === "recording"
    ) {
      recorder.stop();
    }

    setIsRecording(false);

    if (timerRef.current) {
      clearInterval(
        timerRef.current,
      );

      timerRef.current = null;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        /*
         * Recognition may already have stopped.
         */
      }
    }
  }

  /*
   * Upload video + transcript
   */
  async function submitRecording() {
    if (
      interviewComplete
    ) {
      return;
    }

    if (
      !session ||
      !recordingQuestionRef.current
    ) {
      submitInProgressRef.current = false;
      setIsSubmitting(false);

      return;
    }

    /*
     * Do not allow a second POST for the same recording.
     */
    if (
      submittedQuestionIdsRef.current.has(
        recordingQuestionRef.current.id,
      )
    ) {
      console.warn(
        "[browser] Duplicate question submission prevented:",
        recordingQuestionRef.current.id,
      );

      submitInProgressRef.current = false;
      setIsSubmitting(false);

      return;
    }

    /*
     * If another submission is already in progress,
     * do nothing.
     */
    if (
      submitInProgressRef.current &&
      stoppingQuestionIdRef.current !==
        recordingQuestionRef.current.id
    ) {
      console.warn(
        "[browser] Another submission is already in progress.",
      );

      return;
    }

    const question =
      recordingQuestionRef.current;

    const questionId =
      question.id;

    submittedQuestionIdsRef.current.add(
      questionId,
    );
    setLockedQuestionIds((current) => new Set(current).add(questionId));

    submitInProgressRef.current = true;

    setIsSubmitting(true);
    setError("");
    setSubmissionFailed(false);

    /*
     * Capture stable values BEFORE the async
     * network request begins.
     */
    const sessionId =
      session.session_id;

    const transcriptText =
      transcriptRef.current.trim() ||
      "No transcript captured.";

    const startedAt =
      recordingStartedAtRef.current;

    const finalRecordingSeconds =
      startedAt
        ? Math.max(
            0,
            Math.floor(
              (getCurrentTimestamp() -
                startedAt) /
                1000,
            ),
          )
        : recordingSeconds;

    try {
      const recorder =
        mediaRecorderRef.current;

      const mimeType =
        recorder?.mimeType ||
        "video/webm";

      const videoBlob =
        new Blob(
          recordedChunksRef.current,
          {
            type: mimeType,
          },
        );

      if (videoBlob.size === 0) {
        throw new Error(
          "Recorded video is empty.",
        );
      }

      const formData =
        new FormData();

      formData.append(
        "transcript_text",
        transcriptText,
      );

      formData.append(
        "time_taken_seconds",
        String(
          finalRecordingSeconds,
        ),
      );

      const extension =
        mimeType.includes("mp4")
          ? "mp4"
          : "webm";

      formData.append(
        "video",
        videoBlob,
        `interview-${questionId}.${extension}`,
      );

      console.log(
        "[browser] Submitting answer:",
        {
          sessionId,
          questionId,
          videoSize: videoBlob.size,
          transcriptLength:
            transcriptText.length,
          timeTaken:
            finalRecordingSeconds,
        },
      );

      const response = await apiFetch(
        `/interviews/${sessionId}/questions/${questionId}/answer`,
        { method: "POST", body: formData },
      );

      const rawResponse =
        await response.text();

      let data: unknown = null;

      try {
        data = rawResponse
          ? JSON.parse(rawResponse)
          : null;
      } catch {
        data = rawResponse;
      }

      console.log(
        "[browser] Submit answer response:",
        {
          status: response.status,
          statusText:
            response.statusText,
          data,
        },
      );

      if (!response.ok) {
        let message =
          "Failed to submit answer.";

        if (
          typeof data === "object" &&
          data !== null &&
          "detail" in data
        ) {
          message = String(
            (data as { detail: unknown }).detail,
          );
        } else if (
          typeof data === "string" &&
          data.trim()
        ) {
          message = data;
        }

        throw new Error(
          `${response.status}: ${message}`,
        );
      }

      const answerData =
        data as QuestionAnswerResponse;

      /*
       * Backend successfully accepted this question.
       */
      submittedQuestionIdsRef.current.add(
        questionId,
      );

      stoppingQuestionIdRef.current =
        null;

      /*
       * Clear recording data because the backend
       * successfully accepted the answer.
       */
      recordedChunksRef.current = [];

      recordingQuestionRef.current =
        null;

      recordingStartedAtRef.current =
        null;

      setRecordingSeconds(0);

      setTranscript("");
      transcriptRef.current = "";

      /*
       * =====================================================
       * FINAL QUESTION / INTERVIEW COMPLETION
       * =====================================================
       *
       * The backend explicitly tells us that the interview
       * is complete.
       *
       * We do NOT wait for another question.
       *
       * We do NOT enable recording again.
       *
       * We immediately switch to the completion screen.
       */
      if (
        answerData.status ===
        "completed"
      ) {
        console.log(
          "[browser] Interview completed.",
        );

        /*
         * Persist the completion state for this
         * browser tab in case the page reloads.
         */
        try {
          sessionStorage.setItem(
            "hiresense_interview_complete",
            JSON.stringify({ sessionId, completed: true }),
          );
        } catch (storageError) {
          console.warn("[browser] Could not save completion state:", storageError);
        }

        /*
         * Stop any remaining speech.
         */
        if (
          typeof window !== "undefined" &&
          "speechSynthesis" in window
        ) {
          window.speechSynthesis.cancel();
        }

        /*
         * Stop speech recognition if it is
         * still active.
         */
        if (recognitionRef.current) {
          try {
            recognitionRef.current.stop();
          } catch {
            // Ignore if already stopped.
          }
        }

        /*
         * Stop the camera/microphone because
         * the interview is over.
         */
        if (mediaStreamRef.current) {
          mediaStreamRef.current
            .getTracks()
            .forEach((track) => {
              track.stop();
            });

          mediaStreamRef.current = null;
        }
        stopMicrophoneMeter();

        setMediaReady(false);

        /*
         * Most important state changes:
         *
         * currentQuestion = null
         * interviewComplete = true
         */
        setCurrentQuestion(null);
        setInterviewComplete(true);
        setPostAnalysisLoading(true);
        setRestoredSessionId(sessionId);

        /*
        * Start post-interview video analysis.
        *
        * Important:
        * This happens only after the backend has confirmed
        * that the interview is completed and the completion
        * screen state has been activated.
        */
        try {
          console.log(
            "[browser] Starting post-interview video analysis...",
          );

          const videoAnalysisResponse = await apiFetch(
            `/interviews/${sessionId}/video-analysis`,
            { method: "POST" },
          );

          const videoAnalysisData =
            await videoAnalysisResponse.json();

          if (!videoAnalysisResponse.ok) {
            console.error(
              "[browser] Video analysis failed:",
              videoAnalysisData,
            );

            setPostAnalysisLoading(false);
          } else {
            router.push(`/interviews/${sessionId}/results`);
            return;
          }
        } catch (videoAnalysisError) {
          console.error(
            "[browser] Video analysis request error:",
            videoAnalysisError,
          );

          setPostAnalysisLoading(false);
        }
      }

      /*
       * =====================================================
       * NEXT QUESTION
       * =====================================================
       */

      /*
       * =====================================================
       * NEXT QUESTION
       * =====================================================
       */
      if (answerData.next_question) {
        console.log(
          "[browser] Moving to next question:",
          answerData.next_question.id,
        );

        setCurrentQuestion(
          answerData.next_question,
        );

        setIsRecording(false);

        return;
      }

      /*
       * Safety fallback:
       *
       * If the backend did not provide a next question
       * but also did not explicitly return "completed",
       * log it instead of blindly asking the same question.
       */
      console.warn(
        "[browser] No next question was returned and interview was not marked completed.",
        answerData,
      );
    } catch (err) {
      console.error(
        "[browser] Submit answer error:",
        err,
      );

      /*
       * Remove the question from the successful-submission
       * set when the request fails.
       *
       * This allows Retry Submission to send it again.
       */
      submittedQuestionIdsRef.current.delete(
        questionId,
      );

      stoppingQuestionIdRef.current =
        null;

      if (
        err instanceof TypeError &&
        err.message === "Failed to fetch"
      ) {
        setError(
          "Could not reach the HireSense backend while submitting your answer. Check that the backend is still running on http://localhost:8000.",
        );
      } else {
        const message =
          err instanceof Error
            ? err.message
            : "Unknown error";

        setError(
          `Unable to submit the answer: ${message}`,
        );
      }

      /*
       * Keep the recorded chunks intact so the
       * user can retry instead of losing the answer.
       */
      setSubmissionFailed(true);
    } finally {
      submitInProgressRef.current =
        false;

      setIsSubmitting(false);
    }
  }

  /*
   * Retry the last failed submission
   */
  function retrySubmission() {
    if (
      submitInProgressRef.current
    ) {
      return;
    }

    if (
      !recordedChunksRef.current ||
      recordedChunksRef.current.length === 0
    ) {
      setError(
        "The previous recording is no longer available. Please record the answer again.",
      );

      setSubmissionFailed(false);

      return;
    }

    if (recordingQuestionRef.current) {
      submittedQuestionIdsRef.current.delete(
        recordingQuestionRef.current.id,
      );

      stoppingQuestionIdRef.current =
        recordingQuestionRef.current.id;
    }

    void submitRecording();
  }

  /*
   * Cleanup
   */
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(
          timerRef.current,
        );
      }

      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore cleanup errors.
        }
      }

      if (mediaStreamRef.current) {
        mediaStreamRef.current
          .getTracks()
          .forEach((track) => {
            track.stop();
          });
      }
      if (microphoneAnimationRef.current !== null) {
        cancelAnimationFrame(microphoneAnimationRef.current);
      }
      if (audioContextRef.current) {
        void audioContextRef.current.close();
      }

      if (
        typeof window !== "undefined" &&
        "speechSynthesis" in window
      ) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  /*
   * =====================================================
   * INTERVIEW COMPLETE SCREEN
   * =====================================================
   */
  if (
    interviewComplete
  ) {
    return (
      <main className="min-h-[calc(100svh-4rem)] px-4 py-10 text-white sm:px-6">
        <div className="mx-auto flex min-h-[calc(100svh-9rem)] w-full max-w-4xl flex-col items-center justify-center text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-3xl border border-violet-300/20 bg-gradient-to-br from-violet-500/20 to-cyan-400/10 shadow-glow">
            <span className="text-4xl">
              ✓
            </span>
          </div>

          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
            Interview studio
          </p>

          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
            You did it.
          </h1>

          <p className="mt-4 max-w-xl text-base leading-7 text-zinc-400 sm:text-lg">
            Your practice session is complete. Take a moment to reflect — your feedback is being prepared.
          </p>

          <div className="studio-surface mt-8 w-full max-w-xl p-5 text-left sm:p-6">
            {postAnalysisLoading ? (
              <>
                <div className="flex items-center justify-center gap-3">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-violet-300" />

                  <p className="font-medium text-zinc-200">
                    Your feedback is on its way
                  </p>
                </div>
                {error && (
                  <p role="alert" className="mb-5 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm leading-6 text-red-200">
                    {error}
                  </p>
                )}

                <p className="mt-3 text-center text-sm leading-6 text-zinc-400">
                  We’re putting together your answers, voice, and presence insights.
                </p>

                <ol aria-label="Feedback preparation steps" className="mt-6 grid gap-3 sm:grid-cols-2">
                  {["Transcribing your answers", "Reviewing voice patterns", "Reviewing visual presence", "Writing your feedback"].map((step, index) => (
                    <li key={step} className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-black/10 p-3">
                      <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold ${index === 0 ? "bg-emerald-400/10 text-emerald-200" : "bg-violet-400/10 text-violet-200"}`}>
                        {index === 0 ? "✓" : index + 1}
                      </span>
                      <span className="text-xs font-medium text-zinc-300">{step}</span>
                    </li>
                  ))}
                </ol>
                <p className="mt-4 text-center text-xs leading-5 text-zinc-500">
                  Some analysis steps run together. This may take a little while — keep this page open.
                </p>
              </>
            ) : (
              <>
                <div className="flex items-center justify-center gap-3">
                  <div className="h-2.5 w-2.5 rounded-full bg-red-400" />

                  <p className="font-medium text-zinc-200">
                    Evaluation could not be completed
                  </p>
                </div>

                <p className="mt-3 text-sm leading-6 text-zinc-500">
                  We could not finish the post-interview
                  analysis. Please try again.
                </p>
              </>
            )
            }
          </div>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button
              type="button"
              onClick={navigateHome}
              className="rounded-xl border border-zinc-700 px-5 py-3 text-sm font-semibold text-zinc-200 transition hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
            >
              Back to Home
            </button>
            {(session?.session_id || restoredSessionId) && (
              <button
                type="button"
                onClick={() => router.push(`/interviews/${session?.session_id || restoredSessionId}/results`)}
                className="rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-300"
              >
                View interview insights
              </button>
            )}
          </div>
        </div>
      </main>
    );
  }

  /*
   * =====================================================
   * INTERVIEW SCREEN
   * =====================================================
   */
  if (
    session &&
    currentQuestion
  ) {
    return (
      <main className="min-h-[calc(100svh-4rem)] px-4 py-6 text-white sm:px-6 lg:px-8">
        <div className="mx-auto flex min-h-[calc(100svh-7rem)] w-full max-w-7xl flex-col">
          <header className="mb-6 flex items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">
                Interview studio
              </p>

              <h1 className="mt-1 text-lg font-semibold text-white sm:text-xl">
                {selectedProfile?.title}
              </h1>
            </div>

            <div className="flex flex-col items-end gap-2">
              <Badge tone="brand">Question {currentQuestion.question_order} of {session.target_question_count}</Badge>
              <span className="rounded-full border border-cyan-300/15 bg-cyan-300/[0.06] px-2.5 py-1 text-[11px] font-medium text-cyan-100">
                {currentQuestion.source === "ai_followup"
                  ? "Adaptive follow-up"
                  : currentQuestion.source === "baseline"
                    ? "Core question"
                    : "Role practice"}
              </span>
            </div>
          </header>

          <div className="mb-5 h-1.5 overflow-hidden rounded-full bg-white/[0.08]" role="progressbar" aria-label="Interview question progress" aria-valuemin={0} aria-valuemax={session.target_question_count} aria-valuenow={currentQuestion.question_order}>
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-300 transition-[width] duration-500"
              style={{ width: `${Math.min(100, (currentQuestion.question_order / session.target_question_count) * 100)}%` }}
            />
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-red-900/50 bg-red-950/30 px-5 py-4 text-sm text-red-300">
              {error}
            </div>
          )}

          <section className="grid flex-1 grid-cols-1 gap-5 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="studio-surface flex flex-col justify-center p-5 sm:p-7">
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-violet-200">
                  Your interviewer
                </p>

                <button
                  type="button"
                  onClick={() => {
                    if (
                      "speechSynthesis" in
                      window
                    ) {
                      window.speechSynthesis.cancel();

                      const utterance =
                        new SpeechSynthesisUtterance(
                          currentQuestion.question_text,
                        );

                      utterance.rate =
                        0.95;

                      window.speechSynthesis.speak(
                        utterance,
                      );
                    }
                  }}
                  className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-zinc-200 transition hover:bg-white/[0.08]"
                >
                  Replay question
                </button>
              </div>

              <div className="mt-7 flex h-8 items-center gap-1.5" aria-hidden="true">
                {[12, 20, 28, 16, 24, 13, 30, 18, 11, 22].map((height, index) => (
                  <span key={index} className="w-1 rounded-full bg-gradient-to-t from-violet-500 to-cyan-300 opacity-80" style={{ height }} />
                ))}
              </div>
              <h2 className="mt-4 text-2xl font-semibold leading-relaxed text-white sm:text-3xl">
                {currentQuestion.question_text}
              </h2>
              <p className="mt-5 text-sm leading-6 text-zinc-400">Take a breath, organize your thoughts, and answer in your own words.</p>
            </div>

            <div className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-black shadow-2xl shadow-black/30">
              <div className="relative aspect-video min-h-56">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className="h-full w-full object-cover"
                />

                {!mediaReady && (
                  <div className="absolute inset-0 flex items-center justify-center bg-zinc-900">
                    <div className="text-center">
                      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-zinc-800 text-2xl">
                        📹
                      </div>

                      <p className="font-medium text-zinc-300">
                        Camera preview
                      </p>

                      <p className="mt-2 text-sm text-zinc-500">
                        Allow camera and microphone
                        access to continue.
                      </p>
                    </div>
                  </div>
                )}

                {isRecording && (
                  <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border border-red-300/20 bg-black/70 px-3 py-2 text-xs font-semibold text-white backdrop-blur">
                    <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />

                    <span>
                      Recording{" "}
                      {Math.floor(
                        recordingSeconds /
                          60,
                      )
                        .toString()
                        .padStart(2, "0")}
                      :
                      {(
                        recordingSeconds % 60
                      )
                        .toString()
                        .padStart(2, "0")}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <details className="studio-surface lg:col-span-2 p-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400">
                <span>Live transcript</span>
                <Badge tone="neutral">Draft · captured as you speak</Badge>
              </summary>
              <p aria-live="polite" className="mt-3 min-h-12 text-sm leading-6 text-zinc-300">
                {transcript || "Your answer will appear here while recording..."}
              </p>
            </details>

            {submissionFailed && (
              <div className="studio-surface lg:col-span-2 border-amber-400/20 bg-amber-400/[0.05] p-5">
                <p className="text-sm font-medium text-yellow-300">
                  Answer submission failed.
                </p>

                <p className="mt-2 text-sm text-yellow-500/80">
                  Your recording has been kept in memory.
                  Check the backend and retry the submission.
                </p>

                <button
                  type="button"
                  onClick={retrySubmission}
                  disabled={isSubmitting}
                  className="mt-4 rounded-full bg-yellow-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-yellow-500 disabled:cursor-not-allowed disabled:bg-zinc-800"
                >
                  Retry Submission
                </button>
              </div>
            )}

            <div className="flex flex-col items-center justify-center gap-4 lg:col-span-2">
              {!isRecording ? (
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={
                    !mediaReady ||
                    isSubmitting ||
                    submissionFailed ||
                    lockedQuestionIds.has(currentQuestion.id)
                  }
                  className="rounded-full bg-gradient-to-r from-violet-600 to-violet-500 px-9 py-3.5 font-semibold text-white shadow-lg shadow-violet-950/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
                >
                  {!mediaReady
                    ? "Camera Loading..."
                    : submissionFailed
                      ? "Retry Submission Above"
                      : isSubmitting
                        ? "Submitting..."
                        : "Start Recording"}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopRecording}
                  disabled={isSubmitting}
                  className="rounded-full bg-gradient-to-r from-rose-600 to-red-500 px-9 py-3.5 font-semibold text-white shadow-lg shadow-red-950/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-800"
                >
                  Stop & Submit
                </button>
              )}

              {isSubmitting && (
                <p className="text-sm text-zinc-500">
                  Uploading your answer and
                  processing evaluation...
                </p>
              )}

              {!mediaReady &&
                !error && (
                  <p className="text-sm text-zinc-600">
                    Waiting for camera and
                    microphone permission.
                  </p>
                )}
            </div>
          </section>
        </div>
      </main>
    );
  }

  const recommendedProfiles = profiles.filter((profile) => profile.recommended);
  const renderProfileCard = (profile: JobProfile) => {
    const selected = selectedProfile?.id === profile.id;
    const hasMatchScore = profile.match_percent !== undefined
      && profile.match_percent !== null;
    return (
      <button
        key={profile.id}
        type="button"
        onClick={() => setSelectedProfile(profile)}
        className={`group rounded-2xl border p-6 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400 ${
          selected
            ? "border-violet-500 bg-violet-500/10"
            : "border-zinc-800 bg-zinc-900 hover:border-zinc-700 hover:bg-zinc-900/80"
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-semibold text-zinc-100">{profile.title}</h3>
              <span className="text-xs font-semibold text-violet-300">
                {hasMatchScore
                  ? `${profile.match_percent}% match`
                  : "Upload a resume to see your match"}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-zinc-400">{profile.description}</p>
            <div
              role="progressbar"
              aria-label={`${profile.title} resume match`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={profile.match_percent ?? 0}
              className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-800"
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400 transition-[width]"
                style={{ width: `${profile.match_percent ?? 0}%` }}
              />
            </div>
            {profile.matched_skills && profile.matched_skills.length > 0 && (
              <p className="mt-3 text-xs leading-5 text-zinc-500">
                Matches: {profile.matched_skills.join(", ")}
              </p>
            )}
          </div>
          <span className={`mt-1 h-5 w-5 shrink-0 rounded-full border ${
            selected ? "border-violet-400 bg-violet-500" : "border-zinc-700"
          }`} />
        </div>
      </button>
    );
  };

  if (readinessOpen && !session) {
    const checks = [
      ["quiet", "I have a quiet space"],
      ["centred", "My face is centred in the frame"],
      ["light", "My space has good lighting"],
    ];

    return (
      <main className="min-h-[calc(100svh-4rem)] px-4 py-8 text-white sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-6xl">
          <button
            type="button"
            onClick={cancelReadiness}
            className="mb-6 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-zinc-300 transition hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
          >
            ← Choose another role
          </button>
          <div className="mb-7">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">Before you begin</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Settle into your interview space.</h1>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              {selectedProfile?.title} · Check your camera and microphone, then begin when you feel ready.
            </p>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
            <div className="studio-surface overflow-hidden p-3 sm:p-4">
              <div className="relative aspect-video overflow-hidden rounded-2xl bg-black">
                <video
                  ref={readinessVideoRef}
                  autoPlay
                  muted
                  playsInline
                  aria-label="Live camera preview"
                  className="h-full w-full object-cover"
                />
                {!mediaReady && (
                  <div className="absolute inset-0 grid place-content-center bg-zinc-900 px-6 text-center">
                    <span aria-hidden="true" className="text-3xl">◉</span>
                    <p className="mt-3 text-sm font-medium text-zinc-200">
                      {readinessLoading ? "Connecting your camera and microphone…" : "Camera preview is not available"}
                    </p>
                  </div>
                )}
                {mediaReady && (
                  <span className="absolute left-3 top-3 rounded-full border border-emerald-300/20 bg-black/70 px-3 py-1.5 text-xs font-semibold text-emerald-200">
                    Camera ready
                  </span>
                )}
              </div>
            </div>

            <div className="studio-surface p-5 sm:p-6">
              <h2 className="text-base font-semibold text-white">Readiness check</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">Your camera and microphone stay on only during practice.</p>

              <div className="mt-5 rounded-xl border border-white/[0.07] bg-black/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-zinc-200">Microphone level</span>
                  <span className="text-xs text-zinc-400">{microphoneLevel > 8 ? "Sound detected" : "Say a few words"}</span>
                </div>
                <div
                  role="progressbar"
                  aria-label="Live microphone input level"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={microphoneLevel}
                  className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/[0.08]"
                >
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-300 transition-[width] duration-100"
                    style={{ width: `${microphoneLevel}%` }}
                  />
                </div>
              </div>

              <fieldset className="mt-5 space-y-3">
                <legend className="mb-3 text-xs font-semibold uppercase tracking-wide text-zinc-400">A few quick checks</legend>
                {checks.map(([id, label]) => (
                  <label key={id} className="flex cursor-pointer items-center gap-3 text-sm text-zinc-300">
                    <input
                      type="checkbox"
                      checked={readinessChecks.includes(id)}
                      onChange={() => toggleReadinessCheck(id)}
                      className="h-4 w-4 accent-violet-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-400"
                    />
                    {label}
                  </label>
                ))}
              </fieldset>

              {readinessError && (
                <p role="alert" className="mt-5 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm leading-6 text-red-200">
                  {readinessError}
                </p>
              )}

              <div className="mt-6 flex flex-col gap-3">
                {readinessError && (
                  <button
                    type="button"
                    onClick={() => void prepareInterview(selectedProfile)}
                    disabled={readinessLoading}
                    className="w-full rounded-xl border border-white/10 px-5 py-3 text-sm font-semibold text-zinc-200 transition hover:bg-white/[0.06] disabled:opacity-50"
                  >
                    Try camera and microphone again
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => void startInterviewForProfile(selectedProfile)}
                  disabled={!mediaReady || startingInterview || readinessLoading}
                  className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-violet-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-950/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {startingInterview ? "Preparing your session…" : "Begin interview"}
                </button>
                <p className="text-center text-xs leading-5 text-zinc-500">The checklist is optional. You can begin whenever you’re ready.</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  /*
   * =====================================================
   * PROFILE SELECTION
   * =====================================================
   */
  return (
    <main className="min-h-[calc(100svh-4rem)] px-4 py-8 text-white sm:px-6 lg:px-8">
      <div className="mx-auto min-h-[calc(100svh-4rem)] w-full max-w-7xl py-4 sm:py-8">
        <header className="mb-8">
          <button
            type="button"
            onClick={navigateHome}
            className="mb-6 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-zinc-300 transition hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
          >
            ← Home
          </button>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
            Your interview studio
          </p>

          <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
            Find a role to <span className="bg-gradient-to-r from-violet-300 to-cyan-300 bg-clip-text text-transparent">practice for.</span>
          </h1>

          <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-400">
            Choose a profile and settle into a focused, adaptive practice session.
          </p>
        </header>

        {error && (
          <div className="mb-8 rounded-xl border border-red-900/50 bg-red-950/30 px-5 py-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {loadingProfiles ? (
          <div
            aria-label="Loading job profiles"
            role="status"
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            {Array.from({ length: 3 }, (_, index) => (
              <div
                key={index}
                className="animate-pulse rounded-2xl border border-zinc-800 bg-zinc-900 p-6"
              >
                <div className="h-5 w-2/3 rounded bg-zinc-800" />
                <div className="mt-4 h-3 w-full rounded bg-zinc-800" />
                <div className="mt-2 h-3 w-4/5 rounded bg-zinc-800" />
                <div className="mt-5 h-2 rounded-full bg-zinc-800" />
              </div>
            ))}
          </div>
        ) : profiles.length === 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-8 text-center">
            <p className="font-medium text-zinc-300">
              No job profiles available.
            </p>

            <p className="mt-2 text-sm text-zinc-500">
              Check that your backend database has
              been seeded correctly.
            </p>
          </div>
        ) : (
          <>
            {recommendationWarning && (
              <p
                role="status"
                className="mb-5 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] px-4 py-3 text-sm text-amber-100"
              >
                Recommendations are unavailable right now. You can still choose any role below.
              </p>
            )}
            {resumeRequired && (
              <div className="mb-6 flex flex-col gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4 text-sm text-amber-100 sm:flex-row sm:items-center sm:justify-between">
                <span>Add a resume to see personalized role recommendations. You can still choose any role below.</span>
                <Link href="/resume" className="font-semibold text-violet-300 underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400">
                  Upload a resume
                </Link>
              </div>
            )}

            {recommendationMessage && !resumeRequired && (
              <p className="mb-5 rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 py-3 text-sm text-zinc-300">
                {recommendationMessage}
              </p>
            )}

            {recommendedProfiles.length > 0 && (
              <section className="mb-9">
                <div className="mb-4 flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">A good place to start</p>
                    <h2 className="mt-1 text-xl font-bold text-white">Recommended for you</h2>
                  </div>
                  <span className="hidden text-xs text-zinc-500 sm:block">Based on your resume skills</span>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {recommendedProfiles.map((profile) => {
                    const selected = selectedProfile?.id === profile.id;
                    return (
                      <article
                        key={profile.id}
                        className={`studio-surface relative overflow-hidden p-5 transition sm:p-6 ${
                          selected
                            ? "border-violet-300/40 ring-1 ring-violet-400/20"
                            : "hover:border-violet-300/20"
                        }`}
                      >
                        <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-violet-500/10 blur-3xl" />
                        <div className="flex items-start justify-between gap-4">
                          <button
                            type="button"
                            onClick={() => setSelectedProfile(profile)}
                            className="text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
                            aria-pressed={selected}
                          >
                            <h3 className="text-xl font-semibold text-white">{profile.title}</h3>
                          </button>
                          {profile.badge && (
                            <span className="shrink-0 rounded-full border border-violet-300/20 bg-violet-300/[0.08] px-3 py-1 text-xs font-semibold text-violet-200">
                              {profile.badge}
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-sm leading-6 text-zinc-400">{profile.description}</p>
                        <div className="mt-5 flex items-center gap-4">
                          <ProgressRing value={profile.match_percent == null ? null : profile.match_percent / 10} size={68} stroke={6} />
                          <div>
                            <p className="text-sm font-semibold text-violet-200">{profile.match_percent ?? 0}% profile match</p>
                            <p className="mt-1 text-xs text-zinc-400">A starting point, not a scorecard.</p>
                          </div>
                        </div>
                        <div
                          role="progressbar"
                          aria-label={`${profile.title} resume match`}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={profile.match_percent ?? 0}
                          className="mt-2 h-2 overflow-hidden rounded-full bg-white/[0.08]"
                        >
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-300"
                            style={{ width: `${profile.match_percent ?? 0}%` }}
                          />
                        </div>
                        {profile.matched_skills && profile.matched_skills.length > 0 && (
                          <div className="mt-5">
                            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                              Skills you already list
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {profile.matched_skills.map((skill) => (
                                <span
                                  key={skill}
                                  className="rounded-full border border-emerald-300/20 bg-emerald-300/[0.06] px-2.5 py-1 text-xs text-emerald-100"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {profile.missing_skills && profile.missing_skills.length > 0 && (
                          <div className="mt-4">
                            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                              Skills to strengthen
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {profile.missing_skills.slice(0, 3).map((skill) => (
                                <span
                                  key={skill}
                                  className="rounded-full border border-amber-300/20 bg-amber-300/[0.06] px-2.5 py-1 text-xs text-amber-100"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {profile.reason && (
                          <p className="mt-5 text-sm leading-6 text-zinc-300">{profile.reason}</p>
                        )}
                        <button
                          type="button"
                          onClick={() => void prepareInterview(profile)}
                          disabled={startingInterview || readinessLoading}
                          className="mt-6 w-full rounded-xl bg-gradient-to-r from-violet-600 to-violet-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-950/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
                        >
                          {readinessLoading ? "Checking setup..." : "Prepare interview"}
                        </button>
                      </article>
                    );
                  })}
                </div>
              </section>
            )}
            <section>
              <h2 className="mb-4 text-lg font-semibold text-white">Explore all roles</h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {profiles.map(renderProfileCard)}
              </div>
            </section>

            <div className="sticky bottom-3 z-20 mt-10 flex flex-col items-center justify-between gap-4 rounded-2xl border border-white/10 bg-surface-900/90 p-4 shadow-2xl backdrop-blur-xl sm:flex-row sm:px-6">
              <p className="text-sm text-zinc-500">
                {selectedProfile
                  ? `Selected: ${selectedProfile.title}`
                  : "Select a profile to continue."}
              </p>

              <button
                type="button"
                onClick={startInterview}
                disabled={
                  !selectedProfile ||
                  startingInterview ||
                  readinessLoading
                }
                className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-violet-500 px-8 py-3 font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500 sm:w-auto"
              >
                {readinessLoading
                  ? "Checking setup..."
                  : "Prepare interview"}
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default function InterviewPage() {
  return (
    <AuthGuard>
      <InterviewFlow />
    </AuthGuard>
  );
}
