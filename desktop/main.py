import sys
import time

import serial

import config
import ui
from capture import HoldCapture
from llm import create_provider
from logger import get_logger
from memory import Memory
from planner import Planner
from serial_manager import SerialManager
from speech_to_text import SpeechToText
from text_to_speech import TextToSpeech

log = get_logger("main")


class Knoc8:
    def __init__(self) -> None:
        log.info("Starting %s Desktop Agent...", config.ASSISTANT_NAME)
        ui.section("Starting up")

        self.memory = Memory()
        ui.setup_step("Memory", f"{len(self.memory.facts)} facts, "
                                f"{len(self.memory.journal)} journal entries")

        with ui.task("AI provider") as t:
            provider = create_provider()
            t.update(f"{config.LLM_PROVIDER} - {getattr(provider, 'model', '?')}")
        self.planner = Planner(provider, self.memory)

        self.stt = SpeechToText()
        with ui.task("Speech model") as t:
            t.update(f"whisper {config.WHISPER_MODEL} - first run downloads it")
            self.stt.preload()
            t.update(f"whisper {config.WHISPER_MODEL} on {self.stt.device}")

        self.tts = TextToSpeech()
        self.serial = SerialManager()

    # ------------------------------------------------------------------ run

    def run(self) -> None:
        with ui.task("Device") as t:
            connected = self.serial.connect()
            t.update(self.serial.port if connected else "not found - text mode")
        if connected:
            self._hardware_loop()
        else:
            log.warning("ESP32 not found on %s - falling back to text mode.",
                        config.SERIAL_PORT)
            self._text_loop()

    # -------------------------------------------------------- hardware loop

    def _hardware_loop(self) -> None:
        from audio_dsp import HighPassFilter, clean_for_asr

        capture = HoldCapture()
        highpass = HighPassFilter()
        self._highpass = highpass
        recording = False

        self.serial.send_status("IDLE")
        ui.ready("Hold the button, speak, then let go")
        log.info("Hold-to-talk active on %s.", self.serial.port)

        try:
            while True:
                event = self.serial.poll()
                if event is None:
                    time.sleep(0.002)          # don't spin a core
                    continue
                kind, payload = event

                if kind == "line":
                    line = str(payload)
                    if line.startswith("LOG:"):
                        log.debug("ESP32 %s", line)
                    elif line.startswith("BUTTON:DOWN"):
                        recording = True
                        capture.reset()
                        self.serial.send_status("LISTENING")
                        ui.listening()
                    elif line.startswith("BUTTON:UP"):
                        if not recording:
                            continue
                        recording = False
                        self._finish_recording(capture, clean_for_asr)
                    continue

                if not recording:
                    continue

                if not capture.feed(highpass.process(payload)):
                    # held past the maximum — cut it off ourselves
                    recording = False
                    self.serial.send_rec_stop()
                    ui.warn(f"Maximum hold reached ({config.MAX_HOLD_MS // 1000}s)")
                    self._finish_recording(capture, clean_for_asr)

        except KeyboardInterrupt:
            log.info("Shutting down.")
            ui.bye()
        except serial.SerialException as exc:
            log.warning("ESP32 disconnected (%s) - exiting.", exc)
            ui.warn("Device disconnected.")
        finally:
            try:
                self.serial.send_status("IDLE")
            except Exception:
                pass
            self.serial.close()

    def _finish_recording(self, capture, denoise) -> None:
        """Button released (or max hold hit) — validate and process the audio."""
        note = capture.level_note()
        too_short = capture.too_short
        too_quiet = capture.too_quiet
        audio = capture.finish()
        capture.reset()

        if not audio:
            self.serial.send_status("IDLE")
            ui.cancelled("No audio arrived from the device — check the mic wiring")
            return
        if too_short:
            self.serial.send_status("IDLE")
            ui.cancelled(f"Too short ({note}) — hold the button while you speak")
            return
        if too_quiet:
            # Still transcribe it, but say plainly that the mic is near-silent.
            ui.warn(f"Mic level very low ({note})")

        self._handle_utterance(audio, denoise, note)
        self.serial.send_status("IDLE")

    def _handle_utterance(self, audio: bytes, denoise, note: str = "") -> None:
        self.serial.send_status("THINKING")
        ui.thinking_start()
        try:
            text = self.stt.transcribe(denoise(audio))
        except Exception as exc:
            # One bad transcription must never kill the agent.
            log.error("Transcription failed: %s", exc, exc_info=True)
            ui.error(f"Speech recognition failed: {exc}")
            return
        finally:
            ui.thinking_stop()

        if not text:
            self.serial.drain()
            ui.cancelled(f"Couldn't make that out ({note})" if note
                         else "Couldn't make that out")
            return

        ui.heard(text)
        if note:
            ui.info(note)
        ui.thinking_start()
        try:
            reply = self.planner.handle(
                text,
                confirm=self._confirm,
                on_status=self.serial.send_status,
                on_step=self._on_step,
            )
        finally:
            ui.thinking_stop()

        ui.reply(reply)
        self.serial.send_status("SPEAKING")
        self.serial.drain()
        if self._speak_interruptible(reply):
            log.info("Interrupted by button.")
            ui.info("interrupted")
        elif self.planner.awaiting_reply:
            ui.info("hold the button to answer")

    def _on_step(self, tool: str, action: str, detail: str, state: str) -> None:
        if state == "run":
            self.serial.send_step(f"{action}: {detail}" if detail else action)
        ui.step(tool, action, detail, state)

    # ------------------------------------------------------------ text mode

    def _text_loop(self) -> None:
        ui.ready("type a command below, or 'quit' to exit")
        while True:
            try:
                text = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in {"quit", "exit"}:
                break
            ui.thinking_start()
            try:
                reply = self.planner.handle(
                    text, confirm=self._confirm, on_step=self._on_step_text)
            finally:
                ui.thinking_stop()
            ui.reply(reply)
            try:
                self.tts.speak_local(reply)
            except Exception as exc:
                log.warning("Local TTS failed: %s", exc)
        ui.bye()

    @staticmethod
    def _on_step_text(tool: str, action: str, detail: str, state: str) -> None:
        ui.step(tool, action, detail, state)

    # ---------------------------------------------------------------- speech

    def _speak_interruptible(self, text: str) -> bool:
        """Speak, watching for a button press to cut it off."""
        try:
            proc = self.tts.speak_local_async(text)
        except Exception as exc:
            log.warning("TTS failed: %s", exc)
            return False
        deadline = time.time() + 60
        interrupted = False
        while proc.poll() is None and time.time() < deadline:
            event = self.serial.poll()
            if event is None:
                time.sleep(0.005)
                continue
            if event[0] == "line" and str(event[1]).startswith("BUTTON:DOWN"):
                proc.kill()
                interrupted = True
                break
        if proc.poll() is None:
            proc.kill()
        return interrupted

    # --------------------------------------------------------------- confirm

    def _confirm(self, description: str) -> bool:
        import confirm as confirm_mod

        ui.warn("Confirmation required - check the popup")
        if self.serial.connected:
            try:
                self.tts.speak_local_async(
                    "Please confirm. Click yes to allow, or no to cancel."
                )
            except Exception:
                pass
        decided = confirm_mod.confirm(description, timeout=config.CONFIRM_TIMEOUT)
        if self.serial.connected:
            self.serial.drain()
        ui.info("allowed" if decided else "denied")
        return decided


if __name__ == "__main__":
    try:
        ui.banner()
        from bootstrap import needs_setup, run_first_time_setup

        if needs_setup():
            run_first_time_setup()
        Knoc8().run()
    except KeyboardInterrupt:
        ui.bye()
    except Exception as exc:
        log.critical("Fatal error: %s", exc, exc_info=True)
        ui.error(f"Fatal error: {exc}")
        sys.exit(1)
