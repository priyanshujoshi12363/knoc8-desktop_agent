import json
import re
import time
from typing import Callable

import config
import tools
from llm import LLMProvider
from logger import get_logger
from memory import Memory
from tools import terminal
from tools.base import Action

log = get_logger("planner")

_SYSTEM_TEMPLATE = """You are {name}, a voice-controlled desktop operating agent \
running on the user's Windows PC. You control the computer through tools. \
You are helpful, precise, and address the user as "sir".

# Stored memory
{facts}

# Available tools
{catalogue}
## memory
- remember(fact: the fact to store) - Store a fact permanently.
- recall() - List all stored facts.

# Response format
Reply ONLY with a single JSON object, no other text:
{{
  "reply": "<short spoken sentence for the user>",
  "plan": [
    {{"tool": "<tool name>", "action": "<action name>", "args": {{...}}}}
  ]
}}

Rules:
- "plan" may be an empty list [] when the user is just talking or asking a question.
- Use at most {max_steps} steps.
- For terminal work, chain steps: cd first, then run commands one per step.
- Keep "reply" short and natural — it will be spoken aloud.
- Never invent tools or actions that are not in the catalogue."""


class Planner:
    def __init__(self, provider: LLMProvider, memory: Memory) -> None:
        self.provider = provider
        self.memory = memory

    def handle(
        self,
        user_text: str,
        confirm: Callable[[str], bool],
        on_status: Callable[[str], None] = lambda s: None,
    ) -> str:
        start = time.time()
        self.memory.add_turn("user", user_text)

        messages = [{"role": "system", "content": self._system_prompt()}]
        messages += self.memory.conversation()

        on_status("THINKING")
        try:
            raw = self.provider.chat(messages)
        except Exception as exc:
            log.error("LLM request failed: %s", exc)
            return "I could not reach the language model. Please check the connection."

        parsed = self._parse(raw)
        if parsed is None:
            log.warning("Unparseable LLM output: %s", raw[:300])
            return "I did not understand the model response. Please try again."

        reply: str = parsed.get("reply", "Done.")
        plan: list[dict] = parsed.get("plan") or []
        self.memory.add_turn("assistant", json.dumps(parsed, ensure_ascii=False))

        if not plan:
            log.info("Chat-only reply (%.1fs)", time.time() - start)
            return reply

        on_status("EXECUTING")
        results = self._execute(plan[: config.MAX_PLAN_STEPS], confirm)

        summary = self._summarize(user_text, results, fallback=reply)
        log.info("Handled in %.1fs (%d steps)", time.time() - start, len(plan))
        return summary

    def _system_prompt(self) -> str:
        facts = "\n".join(f"- {f}" for f in self.memory.facts) or "(empty)"
        return _SYSTEM_TEMPLATE.format(
            name=config.ASSISTANT_NAME,
            facts=facts,
            catalogue=tools.describe_tools(),
            max_steps=config.MAX_PLAN_STEPS,
        )

    @staticmethod
    def _parse(raw: str) -> dict | None:
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def _execute(self, plan: list[dict], confirm: Callable[[str], bool]) -> list[str]:
        results: list[str] = []
        for i, step in enumerate(plan, 1):
            tool = str(step.get("tool", ""))
            action_name = str(step.get("action", ""))
            args = step.get("args") or {}
            label = f"step {i}: {tool}.{action_name}({args})"
            log.info("Executing %s", label)

            action = self._resolve(tool, action_name)
            if action is None:
                results.append(f"{label} -> unknown tool/action, skipped")
                continue

            if self._needs_confirmation(tool, action, args):
                if not confirm(f"{tool}.{action_name} {args}"):
                    results.append(f"{label} -> DENIED by user")
                    log.warning("User denied %s", label)
                    continue

            try:
                outcome = action.run(**args)
            except Exception as exc:
                outcome = f"ERROR: {exc}"
                log.error("%s failed: %s", label, exc)
            results.append(f"{label} -> {outcome}")

            if isinstance(outcome, str) and (
                outcome.startswith("ERROR") or outcome.startswith("FAILED")
            ):
                results.append("(stopping plan because a step failed)")
                break
        return results

    def _resolve(self, tool: str, action_name: str) -> Action | None:
        if tool == "memory":
            mem_actions = {
                "remember": Action(self.memory.remember, "store a fact",
                                   {"fact": "text"}),
                "recall": Action(lambda: self.memory.recall(), "recall facts"),
            }
            return mem_actions.get(action_name)
        return tools.get_action(tool, action_name)

    @staticmethod
    def _needs_confirmation(tool: str, action: Action, args: dict) -> bool:
        if action.dangerous:
            return True
        if tool == "terminal":
            return terminal.is_dangerous(str(args.get("command", "")))
        return False

    def _summarize(self, user_text: str, results: list[str], fallback: str) -> str:
        report = "\n".join(results)
        self.memory.add_turn("user", f"[TOOL RESULTS]\n{report}")
        try:
            summary = self.provider.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            f"You are {config.ASSISTANT_NAME}. The user asked: "
                            f'"{user_text}". The tool execution results are below. '
                            "Reply with ONE OR TWO short plain sentences to be spoken "
                            "aloud, stating success or failure. End with: "
                            '"What would you like me to do next, sir?" '
                            "No JSON, no markdown."
                        ),
                    },
                    {"role": "user", "content": report},
                ]
            )
            summary = re.sub(r"<think>.*?</think>", "", summary, flags=re.DOTALL).strip()
        except Exception as exc:
            log.error("Summary call failed: %s", exc)
            summary = fallback
        self.memory.add_turn("assistant", summary)
        return summary
