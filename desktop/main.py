import sys
import time

import serial

import config
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
        self.memory = Memory()
        self.planner = Planner(create_provider(), self.memory)
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.serial = SerialManager()

    def run(self) -> None:
        if self.serial.connect():
            self._hardware_loop()
        else:
            log.warning("ESP32 not found on %s — falling back to text mode.",
                        config.SERIAL_PORT)
            self._text_loop()

    def _hardware_loop(self) -> None:
        from audio_dsp import HighPassFilter, denoise_utterance
        from wake_word import UtteranceCapture, WakeWordDetector

        wake = WakeWordDetector()
        capture = UtteranceCapture()
        highpass = HighPassFilter()
        listening = False

        self.serial.send_status("IDLE")
        log.info("Hardware mode active. Say '%s' to start.", config.WAKE_WORD_PHRASE)
        try:
            while True:
                event = self.serial.poll()
                if event is None:
                    continue
                kind, payload = event
                if kind == "line":
                    if str(payload).startswith("LOG:"):
                        log.debug("ESP32 %s", payload)
                    continue

                payload = highpass.process(payload)

                if not listening:
                    if wake.feed(payload):
                        listening = True
                        capture.reset()
                        self.serial.send_status("LISTENING")
                    continue

                audio = capture.feed(payload)
                if audio is None:
                    continue
                listening = False
                if not audio:
                    self.serial.send_status("IDLE")
                    continue

                self.serial.send_status("THINKING")
                text = self.stt.transcribe(denoise_utterance(audio))
                if not text:
                    self.serial.drain()
                    self.serial.send_status("IDLE")
                    continue
                print(f"\nYou said: {text}")
                reply = self.planner.handle(
                    text, confirm=self._confirm, on_status=self.serial.send_status
                )
                print(f"{config.ASSISTANT_NAME}: {reply}")
                self.serial.send_status("SPEAKING")
                interrupted = self._speak_interruptible(reply, wake)
                self.serial.drain()
                wake.reset()
                if interrupted:
                    log.info("Interrupted by wake word — listening.")
                    listening = True
                    capture.reset()
                    self.serial.send_status("LISTENING")
                else:
                    self.serial.send_status("IDLE")
                    log.info("Ready — say '%s' for the next command.",
                             config.WAKE_WORD_PHRASE)
        except KeyboardInterrupt:
            log.info("Shutting down.")
        except serial.SerialException as exc:
            log.warning("ESP32 disconnected (%s) — exiting.", exc)
        finally:
            try:
                self.serial.send_status("IDLE")
            except Exception:
                pass
            self.serial.close()

    def _text_loop(self) -> None:
        print(f"\n{config.ASSISTANT_NAME} text mode — type a command, 'quit' to exit.\n")
        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in {"quit", "exit"}:
                break
            reply = self.planner.handle(text, confirm=self._confirm)
            print(f"{config.ASSISTANT_NAME}: {reply}\n")
            try:
                self.tts.speak_local(reply)
            except Exception as exc:
                log.warning("Local TTS failed: %s", exc)

    def _speak_interruptible(self, text: str, wake) -> bool:
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
                time.sleep(0.01)
                continue
            kind, payload = event
            if kind == "chunk" and wake.feed(payload):
                proc.kill()
                interrupted = True
                break
        if proc.poll() is None:
            proc.kill()
        return interrupted

    @staticmethod
    def _confirm(description: str) -> bool:
        answer = input(f"\n⚠ CONFIRM dangerous action: {description}\n"
                       "Type 'yes' to allow: ").strip().lower()
        return answer in {"y", "yes"}


if __name__ == "__main__":
    try:
        Knoc8().run()
    except Exception as exc:
        log.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)
