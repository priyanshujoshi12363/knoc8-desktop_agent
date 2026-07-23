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
with FULL control of the user's Windows PC. You are helpful, decisive, and \
address the user as "sir".

You can do ANYTHING on this PC through your tools:
- The terminal tool runs ANY Windows shell command: npm, pip, git, python, \
node, mkdir, cd, dir, copy, tasklist, ipconfig, winget — everything. Output \
is captured and returned to you.
- For commands that need administrator rights, run them through the terminal \
as: powershell -Command "Start-Process cmd -ArgumentList '/c <command>' -Verb RunAs" \
(Windows shows the user a UAC confirmation).
- You can open/close any installed application, control keyboard and mouse, \
manage files, windows, volume, and more.

# Stored memory
{facts}

# Recent activity (things you already did for the user, survives restarts)
{activity}

# Chrome profiles on this PC
{chrome_profiles}
Default profile setting: {chrome_default}
When the user asks to open Chrome: if they name a profile, open it with \
browser.open_chrome. If no profile is named and no default is set, ASK by \
voice which profile to use ("plan": [], list the profile names in "reply"), \
then open the chosen one when they answer.

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
- You are a friendly companion, not just a command executor. For greetings \
and small talk ("hello", "how are you", "thank you"), chat naturally and \
warmly with "plan": []. Reference recent activity or memory when relevant.
- When asked "what did I do last" or similar, answer from Recent activity.
- BE DECISIVE. The user is speaking, so transcripts may be imperfect — infer \
the obvious intent and act. Pick sensible defaults for names and paths \
instead of asking (e.g. "a folder on D" -> D:\\NewFolder unless context says \
otherwise; "run the server" -> npm run dev in the current project).
- Only ask a question when the request is truly ambiguous, using "plan": [] \
and putting the question in "reply".
- Speech recognition often garbles tech words: "PM"/"npm", "peep"/"pip", \
"get"/"git", "D file"/"D drive". Correct them from context.
- Use at most {max_steps} steps.
- You CAN do MANY things in one command. Chain every requested task into \
"plan" in order — they execute one by one, top to bottom. Use wait.wait for \
timed actions. Example: "play song co2 for 15 seconds, then close the \
browser and open terminal" becomes: browser.play_youtube(query="co2 song") \
-> wait.wait(seconds=15) -> application.close(name="chrome") -> \
terminal.run(...). Never drop part of a multi-part request.
- If one step fails, the remaining steps still run — mention any failures \
in your summary.
- IMPORTANT: terminal.run executes commands INTERNALLY and returns the \
output to you — you do NOT need to open a terminal window first. When the \
user says "open terminal and run X", just run X with terminal.run and report \
the result. Only open the Terminal app if the user explicitly wants a window \
to work in themselves, or use terminal.run_background for long-running \
servers they should see.
- If a folder or file already exists, do not fail — use it, or pick a \
different name.
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
        on_step: Callable[[str], None] = lambda s: None,
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
        results = self._execute(plan[: config.MAX_PLAN_STEPS], confirm, on_step)

        summary = self._summarize(user_text, results, fallback=reply)
        ok = not any("ERROR" in r or "FAILED" in r or "DENIED" in r for r in results)
        self.memory.log_activity(
            f'"{user_text}" -> {"done" if ok else "had problems"}: {summary[:120]}'
        )
        log.info("Handled in %.1fs (%d steps)", time.time() - start, len(plan))
        return summary

    def _system_prompt(self) -> str:
        from tools.browser import chrome_profiles

        facts = "\n".join(f"- {f}" for f in self.memory.facts) or "(empty)"
        activity = "\n".join(
            f"- {a}" for a in self.memory.recent_activity()
        ) or "(nothing yet)"
        profiles = "\n".join(
            f"- {name}" for name in chrome_profiles().values()
        ) or "(none found)"
        return _SYSTEM_TEMPLATE.format(
            name=config.ASSISTANT_NAME,
            facts=facts,
            activity=activity,
            chrome_profiles=profiles,
            chrome_default=config.CHROME_PROFILE or "(not set — ask)",
            catalogue=tools.describe_tools(),
            max_steps=config.MAX_PLAN_STEPS,
        )

    @staticmethod
    def _parse(raw: str) -> dict | None:
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict) and "reply" in data:
                    return data
            except json.JSONDecodeError:
                pass
        # Model answered in plain text (e.g. a clarifying question) — speak it.
        if raw:
            return {"reply": raw[:400], "plan": []}
        return None

    def _execute(
        self,
        plan: list[dict],
        confirm: Callable[[str], bool],
        on_step: Callable[[str], None] = lambda s: None,
    ) -> list[str]:
        results: list[str] = []
        for i, step in enumerate(plan, 1):
            tool = str(step.get("tool", ""))
            action_name = str(step.get("action", ""))
            args = step.get("args") or {}
            label = f"step {i}: {tool}.{action_name}({args})"
            log.info("Executing %s", label)
            detail = str(next(iter(args.values()), "")).strip()
            on_step(f"{action_name}: {detail}" if detail else f"{tool}.{action_name}")

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
