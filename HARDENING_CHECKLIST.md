# Knoc8 — Safety & Hardening Checklist

**Goal:** Knoc8 keeps **full control of the PC** (that's the product), but is **safe by default** — a misheard word, a random voice, or a malicious webpage can never quietly do damage.

Principle: **Powerful for the owner, harmless to everyone else.**

Legend: 🔴 Critical (broken or exploitable today) · 🟠 High · 🟡 Medium · 🟢 Nice-to-have

---

## 1. Confirmation gate that works by VOICE 🔴  ✅ DONE
The safety gate currently asks for a typed "yes" on the console — useless in device mode.

- [x] Spoken confirmation: Knoc8 says *"Please confirm. Say confirm to allow, or cancel."*
- [x] Native Yes/No popup you can also click (like Claude Code)
- [x] Auto-cancel (default No) if no confirmation within the timeout (20s, configurable)
- [x] Never blocks forever — works headless (no console input needed)
- [ ] OLED ⚠ CONFIRM screen (needs a firmware re-flash — deferred, spoken prompt covers it)

## 2. Safe Mode (default ON for buyers) 🔴  ✅ DONE
A single switch that decides how much power is unlocked.

- [x] **Safe Mode** (default ON): destructive/unknown actions blocked entirely
- [x] **Full Mode**: everything enabled, dangerous actions require confirmation
- [x] Toggle lives in the web settings panel (Safety section)
- [x] Planner enforces it everywhere — blocked actions reported cleanly

## 3. Command execution — allowlist, not denylist 🟠  ✅ DONE
Today's `is_dangerous` regex is a bypassable blocklist.

- [x] Allowlist of known-safe commands (npm, pip, git, dir, cd, python, node…) run freely
- [x] Anything *not* on the allowlist → requires confirmation
- [x] Hard-block class: `format`, `diskpart`, `bcdedit`, Defender-disable, `Set-ExecutionPolicy`, `… | iex`, `schtasks`, `rm -rf /`, recursive deletes
- [x] Chained/piped commands only "safe" if every segment is safe

## 4. Settings web server — close the CSRF hole 🔴  ✅ DONE
Any website the buyer visits could POST to `127.0.0.1:8733` and steal/overwrite their API key.

- [x] Per-launch secret token required on every write — forged requests rejected (403)
- [x] `Origin`/`Referer` validated against localhost
- [x] Token only readable by the real page (cross-origin can't read it)
- [ ] Block non-official `OPENAI_BASE_URL` change (nice-to-have, deferred)

## 5. Secrets handling 🟠  PARTIAL
- [ ] Store API keys with Windows DPAPI (encrypted) — **deferred** (bigger change to config load)
- [x] Never print full keys — masked in UI **and** now redacted from logs (#6)

## 6. Logging & privacy 🟠  ✅ DONE
Logs captured transcripts, terminal output, and file contents in plaintext.

- [x] Redact API keys / tokens / bearer secrets before writing logs (console + file)
- [x] Log rotation + size cap (5 MB × 5)
- [ ] "Clear my data" button (deferred — nice-to-have)

## 7. Voice access control 🟡
Right now anyone who speaks near the mic controls the PC.

- [ ] Destructive actions always need the explicit voice confirm (covers most of the risk)
- [ ] Optional: a spoken PIN/passphrase for Full-Mode destructive actions
- [ ] Optional (v2): speaker verification so only the owner's voice is trusted
- [ ] Ignore commands while it's speaking (avoid self-triggering) — partly done

## 8. Prompt-injection defense 🟡
It reads web pages, files, and clipboard, then feeds them to the LLM.

- [ ] Treat tool-result content as **data, not instructions** in the prompt
- [ ] Never auto-execute a command that came from read content without confirmation
- [ ] Cap how much external text is fed back to the model

## 9. Fail-safes & recovery 🟡  PARTIAL
- [x] Deletes go to the **Recycle Bin** (recoverable), not permanent
- [x] pyautogui fail-safe kept on (mouse to corner aborts)
- [x] Every executed action logged with timestamp
- [ ] Global "stop / cancel" voice command mid-execution (deferred)

## 10. Transparency & consent (for selling) 🟢
- [ ] First-run screen clearly states what Knoc8 can access, buyer clicks "I understand"
- [ ] Short privacy note: voice command text is sent to the chosen LLM cloud
- [ ] Easy full uninstall (remove autostart, files, keys)

---

## Build order (recommended)
1. 🔴 #1 Voice confirmation gate  ← makes the safety actually work
2. 🔴 #4 Settings-server CSRF fix  ← closes the one live exploit
3. 🔴 #2 Safe Mode toggle (default on)  ← the master safety switch
4. 🟠 #3 Command allowlist
5. 🟠 #5 Encrypt keys, #6 redact logs
6. 🟡 #7–#9 voice control, injection, fail-safes
7. 🟢 #10 consent screens (during packaging)

Once #1–#5 are done, the product is genuinely safe to hand to a normal buyer.
