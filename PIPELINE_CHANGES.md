# Coding and voice pipeline changes

The desktop planner now handles `coding.build` and `coding.continue_task`
internally with the selected LLM. It no longer launches Claude or another CLI
for those planner actions. The older README's handoff descriptions refer to
the previous behavior; direct legacy helpers in `tools/coding.py` remain.

Coding runs for at most eight model passes. Each pass can inspect/write files
and execute terminal commands, then reads their results before continuing.
The existing confirmation gate applies to each action. Successful completion
requires a successful terminal step explicitly marked as verification by the
model. This is a model-selected check, not a guarantee of software correctness.
Failed/incomplete work stays in the project folder for a follow-up request.
Shell commands retain the agent's existing PC access; this is not a sandbox.

Simple short tool results and coding results are spoken directly, avoiding an
extra summary request and preventing the old summarizer from claiming a coding
handoff produced a finished executable.

Settings (restart the desktop agent after changing them):

- `KNOC8_LLM_TIMEOUT=30`: per-request timeout; raise for larger coding requests.
  This limits waiting, rather than making a slow server generate faster.
- `KNOC8_LLM_MAX_TOKENS=2048`: now also applies to Ollama generation. Increase
  for larger source files if generation reports the output limit.
- `KNOC8_WHISPER_BEAM_SIZE=3`: decoding effort, configurable in the settings panel.
  Lower values favor speed; recognition quality needs testing on your microphone.
- `KNOC8_WHISPER_LANGUAGE=en`: use `hi` or `auto` if appropriate for your speech.

Speech decoding no longer conditions later segments on earlier decoded text,
and uses a fixed temperature to avoid repeated temperature fallback attempts.
The technical vocabulary prompt includes EXE, PyInstaller, backend and Snake.
The high-pass filter resets for each utterance. Pressing during speech now
preserves that press for the next recording instead of consuming it.

Logs include separate audio cleanup, transcription and Ollama request timings,
plus server-provided generation metrics when available. The missing CUDA DLL
observed in existing logs has not been installed by this change; CPU fallback
remains available.

Run regression tests with:

```
python -m unittest discover -s desktop/tests -v
```

Tests use fake model responses and mocked command execution; they do not certify
live model latency, microphone recognition, or generated application quality.
