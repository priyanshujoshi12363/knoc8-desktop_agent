import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from planner import Planner
from tools import terminal
from speech_to_text import SpeechToText
from main import Knoc8
import numpy as np


def response(plan=None, finished=False):
    return json.dumps({"reply": "Result", "plan": plan or [], "finished": finished})


class PipelineTests(unittest.TestCase):
    def make_planner(self, replies):
        provider = Mock()
        provider.chat.side_effect = replies
        return Planner(provider, Mock())

    def test_simple_result_needs_no_second_call(self):
        p = self.make_planner([])
        self.assertEqual(p._summarize("make folder", ["step 1 -> Created folder"], "Done"), "Created folder")
        p.provider.chat.assert_not_called()

    def test_coding_failure_is_not_rewritten_as_success(self):
        p = self.make_planner([])
        text = p._summarize("build", ["coding.build -> ERROR: Build failed"], "Done")
        self.assertIn("ERROR", text)
        p.provider.chat.assert_not_called()

    def test_coding_reads_errors_then_verifies(self):
        step = {"tool": "terminal", "action": "run", "args": {"command": "python -m unittest"}, "verify": True}
        p = self.make_planner([response([step]), response([step]), response(finished=True)])
        previous = terminal._cwd
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory, patch.object(p, "_execute", side_effect=[
            ["step -> FAILED (exit 1)\nAssertionError"], ["step -> SUCCESS\nOK"]
        ]):
            self.assertTrue(p._code("build", directory, True).startswith("Coding checks completed"))
        self.assertEqual(terminal._cwd, previous)
        self.assertEqual(p.provider.chat.call_count, 3)

    def test_coding_cannot_claim_done_without_check(self):
        p = self.make_planner([response(finished=True)])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            self.assertTrue(p._code("build", directory, True).startswith("ERROR"))

    def test_coding_rejects_recursive_handoff(self):
        p = self.make_planner([response([{"tool": "coding", "action": "build", "args": {}}])])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            self.assertIn("unsupported", p._code("build", directory, True))

    def test_coding_stops_at_budget(self):
        step = {"tool": "filesystem", "action": "list", "args": {}}
        p = self.make_planner([response([step])] * 8)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory, patch.object(p, "_execute", return_value=["step -> contents"]):
            self.assertIn("eight-pass limit", p._code("build", directory, True))
        self.assertEqual(p.provider.chat.call_count, 8)

    def test_speech_uses_explicit_decoding_options(self):
        stt = SpeechToText()
        model = Mock()
        model.transcribe.return_value = ([], None)
        with patch.object(stt, "_ensure_model", return_value=model):
            self.assertEqual(stt._run(np.zeros(16000, dtype=np.float32)), "")
        self.assertFalse(model.transcribe.call_args.kwargs["condition_on_previous_text"])
        self.assertEqual(model.transcribe.call_args.kwargs["temperature"], 0.0)

    def test_interrupt_preserves_button_for_next_recording(self):
        agent = Knoc8.__new__(Knoc8)
        agent._pending_press = False
        agent.tts = Mock()
        proc = agent.tts.speak_local_async.return_value
        proc.poll.return_value = None
        agent.serial = Mock()
        agent.serial.poll.return_value = ("line", "BUTTON:DOWN")
        self.assertTrue(agent._speak_interruptible("hello"))
        self.assertTrue(agent._pending_press)
        proc.kill.assert_called()


if __name__ == "__main__":
    unittest.main()
