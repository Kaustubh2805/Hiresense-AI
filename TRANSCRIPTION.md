# Interview transcription

The backend uses `faster-whisper` on CPU to refine the browser's live draft after each answer. The backend downloads the selected model on its first use and caches it in the `whisper_models` Docker volume mounted at `/models`.

Defaults are `WHISPER_MODEL=small.en`, `WHISPER_COMPUTE_TYPE=int8`, and `WHISPER_CPU_THREADS=4`. The `small.en` model download is approximately 0.5 GB. Machines with limited CPU or memory can set `WHISPER_MODEL=base.en` in the project-root `.env` before starting/rebuilding the backend.

By default, transcription runs asynchronously so answer submission and follow-up generation use the browser transcript without waiting. Post-interview analysis waits up to `WHISPER_WAIT_TIMEOUT_SECONDS` (default 30 seconds) for pending transcriptions, then uses Whisper where available and the browser draft otherwise. Set `WHISPER_SYNC=true` to transcribe before scoring and follow-up generation; this adds transcription time to every answer submission.

Whisper can omit hesitation/filler words. Audio filler measurements compare browser and Whisper text and use the higher detected count; the report notes this limitation. For human transcription-accuracy measurement, use `backend/scripts/compare_transcripts.py` with a manually corrected reference transcript and the generated hypothesis.

Visual analysis uses up to five recorded answers (or all available answers for shorter interviews), sampling at most two frames per second per answer to keep analysis responsive.

Local LLM grammar review is disabled by default because it made seven separate Ollama requests take about 78 seconds in a recent interview. Deterministic language scores remain enabled. Set `ENABLE_LLM_GRAMMAR=true` in the project-root `.env` to opt back into contextual grammar feedback; this can increase analysis time.
