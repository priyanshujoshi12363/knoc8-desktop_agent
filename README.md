<div align="center">

# 🤖 Knoc8 Desktop Agent

**A hands-free, voice-controlled AI agent that operates your Windows PC — with a cute animated face on an OLED.**

*Not a chatbot. A desktop companion that listens, plans, executes, and talks back.*

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![ESP32-C3](https://img.shields.io/badge/ESP32--C3-Arduino-E7352C?logo=espressif&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-MiniMax%20M3%20·%20Ollama%20Cloud-black)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

Say **"Hey Agent"** into the ESP32 mic and give a command. Knoc8 hears the wake word, records what you say, cleans the audio, transcribes it locally, reasons about it with an LLM, plans the steps, executes them on your PC — terminal, apps, browser, files, windows, system controls — and speaks the result back through your PC speakers. All the while a little robot face blinks and reacts on the OLED, showing a live ticker of exactly what it's doing.

> 🗣️ *"Hey Agent, open Chrome with my Priyanshu profile and play the song CO2 on YouTube, let it play 15 seconds, then open terminal and check the npm version."*
> → Knoc8 does all five steps in order and reports back. 🔊 *"All done, sir. What would you like me to do next?"*

---

## ✨ Features

| | |
|---|---|
| 🎙️ **Hands-free wake word** | Say **"Hey Agent"** — no buttons. Fully configurable phrase. |
| ✋ **Barge-in / interrupt** | Say the wake word *while it's talking* to cut it off and give a new command. |
| 🧠 **LLM reasoning + planning** | Turns speech into ordered, validated tool plans. |
| 🔀 **Multi-provider LLM** | Ollama Cloud, **Anthropic Claude**, or **OpenAI** — switch with one setting. |
| 🔗 **Multi-step tasks** | Chains up to 20 actions in one command, with timed `wait` steps. |
| 🖥️ **11 tool modules** | Terminal, apps, browser, keyboard, mouse, clipboard, files, windows, system, notifications, wait. |
| 🌐 **Chrome profile picker** | Reads your real Chrome profiles and asks by voice which one to open. |
| 😊 **Animated OLED face** | Robot eyes that blink, glance, squint, and smile per state + live step ticker. |
| 🔊 **Spoken replies** | Offline Windows TTS through your PC speakers, non-blocking. |
| 🎧 **Noise cancellation** | High-pass filter + spectral denoise for cleaner recognition. |
| 💾 **Persistent memory** | Remembers facts *and* auto-journals every task — survives restarts. |
| 🔌 **Auto-start on plug-in** | A watcher launches the agent automatically when the ESP32 is connected. |
| 🛠️ **Settings CLI** | `python settings.py` to tune everything, no code editing. |
| 🛡️ **Safety gate** | Delete, shutdown, restart & risky shell commands need typed confirmation. |
| ⌨️ **Text mode fallback** | No ESP32? A console REPL runs the same brain. |

---

## 🔁 How It Works

```
🎙️  ESP32-C3 streams mic audio continuously ──► USB Serial (921600 baud) ──► PC
                                                                              │
                                              High-pass filter (kills rumble/hum)
                                                                              │
                                              Wake word detector hears "Hey Agent"
                                                                              │
                                              Silence detection captures the command
                                                                              │
                                              Spectral denoise ─► Whisper (local STT)
                                                                              │
                                              LLM (MiniMax M3) plans JSON tool calls
                                                                              │
                                              Planner validates + executes each step
                                                                              │
😊  OLED face reacts + live step ticker ◄── STATUS/STEP      🔊 TTS reply ◄── LLM summary
```

**Separation of concerns:** the ESP32 is pure hardware — it only streams the mic and animates the face. *All* intelligence runs on the PC. The LLM is swappable behind one interface — `LLMProvider` has `OllamaCloudProvider`, `AnthropicProvider` (Claude, via the official `anthropic` SDK), and `OpenAIProvider` implementations; set `KNOC8_LLM_PROVIDER` to choose. Whichever you pick, the LLM never executes anything directly; it returns a JSON plan that Python validates against a tool registry before running:

```json
{
  "reply": "Opening Chrome and playing that now, sir.",
  "plan": [
    { "tool": "browser", "action": "open_chrome", "args": { "profile": "Priyanshu" } },
    { "tool": "browser", "action": "play_youtube", "args": { "query": "CO2 song" } }
  ]
}
```

---

## 📁 Project Structure

```
knoc8-desktop_agent/
├── esp32/
│   └── firmware.ino          # I2S mic streaming + animated OLED face
└── desktop/
    ├── main.py               # Orchestrator: wake → capture → plan → execute → speak
    ├── watcher.py            # Auto-launches the agent when the ESP32 is plugged in
    ├── settings.py           # Interactive + CLI settings editor (writes .env)
    ├── config.py             # All settings, loaded from .env
    ├── serial_manager.py     # Serial protocol: chunked audio + STATUS/STEP lines
    ├── wake_word.py          # "Hey Agent" detection + silence-based capture (VAD)
    ├── audio_dsp.py          # High-pass filter + spectral noise reduction
    ├── speech_to_text.py     # faster-whisper transcription
    ├── text_to_speech.py     # Offline pyttsx3 TTS (isolated subprocess)
    ├── llm.py                # LLMProvider → Ollama / Claude / OpenAI
    ├── planner.py            # Prompt, JSON parsing, validation, safety, summaries
    ├── memory.py             # Facts + activity journal + conversation history
    ├── logger.py             # Console + rotating file logs
    └── tools/                # One module per capability
        ├── terminal.py       ├── applications.py   ├── browser.py
        ├── filesystem.py     ├── keyboard.py       ├── mouse.py
        ├── clipboard.py      ├── windows.py        ├── system.py
        ├── notification.py   └── wait.py
```

---

## 🛠️ Tool Catalogue

The LLM picks from these; Python executes them.

| Tool | Actions |
|---|---|
| **terminal** | `run` (any shell command, captures output), `run_background` (dev servers), `current_dir` |
| **application** | `open`, `close`, `focus` — with aliases for Chrome, Cursor, VS Code, Terminal, Spotify... |
| **browser** | `open_chrome` (by profile), `list_chrome_profiles`, `open_url`, `search_google`, `search_youtube`, `play_youtube` |
| **filesystem** | `create_file`, `create_folder`, `rename`, `move`, `copy`, `delete` ⚠️, `list`, `read` |
| **keyboard** | `type`, `press`, `hotkey` |
| **mouse** | `move`, `click`, `right_click`, `double_click`, `scroll` |
| **clipboard** | `copy_text`, `copy_selection`, `paste`, `read` |
| **windows** | `list`, `switch`, `maximize`, `minimize` |
| **system** | `set_volume`, `get_volume`, `mute`, `set_brightness`, `lock`, `shutdown` ⚠️, `restart` ⚠️ |
| **notification** | `show` |
| **wait** | `wait` (pause between steps, up to 300s) |
| **memory** | `remember`, `recall` |

⚠️ = requires typed confirmation before running.

Adding a tool = one new module in `tools/` + one line in `tools/__init__.py`.

---

## 😊 OLED Face States

The animated robot face on the SSD1306 reacts to what Knoc8 is doing:

| State | Face |
|---|---|
| **IDLE** | Round eyes that randomly **blink** and glance around · "say hey agent" |
| **LISTENING** | Big **wide** attentive eyes |
| **THINKING** | Squinted eyes darting side-to-side with animated `...` dots |
| **WORKING** | Focused eyes + sliding progress bar + **live text of the current step** |
| **SPEAKING** | Happy bouncing **smile** eyes |

While working, the PC streams each action to the display, so *"make a backend structure"* shows `run: mkdir backend` → `run: npm init -y` → `create_folder: routes` live on screen.

---

## 🔌 Hardware

| Part | Purpose |
|---|---|
| ESP32-C3 dev board | Voice interface (native USB serial) |
| INMP441 | I2S microphone |
| SSD1306 128×64 OLED | Animated face + status (I2C) |

### Wiring (ESP32-C3)

| Component | Pin | ESP32-C3 GPIO |
|---|---|---|
| INMP441 | VCC / GND | 3.3V / GND |
| INMP441 | SCK / WS / SD | 4 / 5 / 2 |
| INMP441 | L/R | GND |
| SSD1306 | VCC / GND | 3.3V / GND |
| SSD1306 | SDA / SCL | 8 / 9 |

> ⚠️ Keep wires away from the C3's internal flash pins (GPIO 11–17) — connecting them corrupts flash access.

Mic audio: **16 kHz · 16-bit · mono PCM** streamed over serial at **921600 baud**. Replies play through the **PC speakers** (there is no speaker on the device).

---

## 🚀 Quick Start

### 1 — Flash the ESP32-C3

1. Open `esp32/firmware.ino` in Arduino IDE (needs the **Arduino-ESP32 core 3.x**).
2. Install **Adafruit SSD1306** + **Adafruit GFX Library** from Library Manager.
3. Select **ESP32C3 Dev Module** on its COM port and upload (upload speed 115200 is safest).

### 2 — Set up the desktop app

```bash
git clone https://github.com/priyanshujoshi12363/knoc8-desktop_agent.git
cd knoc8-desktop_agent/desktop

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### 3 — Configure

Run the settings tool and set at least your Ollama Cloud API key and COM port:

```bash
python settings.py
```

Or create `desktop/.env` by hand (it's git-ignored):

```env
OLLAMA_API_KEY=your-ollama-cloud-api-key
KNOC8_SERIAL_PORT=COM17
```

### 4 — Run

```bash
python main.py
```

- **ESP32 connected** → hardware mode: say **"Hey Agent"**, then your command.
- **No ESP32** → text mode: type commands into the console, same brain.

### 5 — (Optional) Auto-start on plug-in

Point a shortcut at `watcher.py` in your Windows **Startup** folder (`shell:startup`):

```bat
start "" /min pythonw "FULL\PATH\TO\desktop\watcher.py"
```

After each login the watcher runs quietly and launches the agent automatically whenever the ESP32 is connected (and stops it when unplugged).

---

## ⚙️ Configuration

Everything lives in `desktop/.env` (managed by `settings.py`). Change the LLM by editing one variable; swap providers by implementing one new `LLMProvider` subclass.

| Variable | Default | Description |
|---|---|---|
| `KNOC8_LLM_PROVIDER` | `ollama` | `ollama`, `anthropic` (Claude), or `openai` |
| `OLLAMA_API_KEY` | — | Ollama Cloud API key (if using Ollama) |
| `KNOC8_LLM_MODEL` | `minimax-m3` | Ollama model |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (if using Claude) |
| `KNOC8_ANTHROPIC_MODEL` | `claude-opus-4-8` | Claude model |
| `OPENAI_API_KEY` | — | OpenAI API key (if using OpenAI) |
| `KNOC8_OPENAI_MODEL` | `gpt-4o` | OpenAI model |
| `KNOC8_SERIAL_PORT` | `COM16` | ESP32 serial port (auto-detected if wrong) |
| `KNOC8_SERIAL_BAUD` | `921600` | Serial baud rate |
| `KNOC8_WAKE_WORD` | `hey agent` | The wake phrase — set it to anything |
| `KNOC8_WAKE_MODEL` | `tiny` | Whisper size used for wake detection |
| `KNOC8_WHISPER_MODEL` | `base` | Whisper size for commands (`tiny`/`base`/`small`) |
| `KNOC8_MIC_THRESHOLD` | `300` | Mic energy gate (lower = more sensitive) |
| `KNOC8_SILENCE_MS` | `1200` | Silence that ends a command |
| `KNOC8_TTS_RATE` | `175` | Voice speed (words/min) |
| `KNOC8_CHROME_PROFILE` | *(empty)* | Default Chrome profile (empty = ask by voice) |
| `KNOC8_NOISE_REDUCTION` | `1` | Noise cancellation on/off |

CLI shortcuts: `python settings.py list` · `python settings.py get KEY` · `python settings.py set KEY VALUE`.

---

## 🗣️ Example Commands

| Say this | Knoc8 does |
|---|---|
| *"Hello, how are you?"* | Chats back naturally (no action) |
| *"What did I do last?"* | Recalls from its activity journal |
| *"Open Chrome"* | Asks which profile, then opens it |
| *"Play CO2 on YouTube"* | Finds and plays the top video in Chrome |
| *"Make a backend folder on D and run npm init"* | Chains folder + terminal steps |
| *"Run npm install then start the dev server"* | Multi-step terminal execution |
| *"Set volume to 40 and brightness to 70"* | System controls in one command |
| *"Remember my project is Karigar"* | Stores it permanently |
| *"Delete the old backup folder"* | ⚠️ Asks you to confirm first |

---

## 🛡️ Safety

- The LLM only **proposes** tool calls — Python validates every step against the registry before execution.
- **Confirmation required** (typed `yes` in the console) for: file/folder deletion, shutdown, restart, and terminal commands matching dangerous patterns (`rm`, `del`, `format`, `diskpart`, `reg add/delete`, `taskkill /f`, ...).
- Admin commands are relaunched through Windows UAC, so the OS itself prompts you.
- Every command, transcript, and result is logged to `desktop/logs/`.
- `pyautogui` failsafe: slam the mouse into a screen corner to abort automation instantly.

---

## 📡 Serial Protocol

```
PC → ESP32   STATUS:<IDLE|LISTENING|THINKING|EXECUTING|SPEAKING>   (drives the face)
             STEP:<text>                                           (live step ticker)

ESP32 → PC   READY
             CHUNK:<n> + n bytes of raw PCM   (continuous mic stream)
```

Chunk-framing keeps binary audio from ever corrupting line parsing, and the protocol is trivially extendable with new message types.

---

## 🗺️ Roadmap

- [x] Hands-free wake word (*"Hey Agent"*)
- [x] Barge-in interruption while speaking
- [x] Multi-step task chaining
- [x] Animated OLED face + live status
- [x] Chrome profile selection by voice
- [x] Noise cancellation
- [x] Persistent memory + activity journal
- [x] Auto-start on device connect
- [ ] In-page browser automation (click, read, fill forms)
- [ ] Acoustic echo cancellation for cleaner barge-in
- [ ] Camera + computer vision · face recognition
- [ ] Local LLM support · plugin system

---

## 🧰 Tech Stack

**Firmware:** Arduino (ESP32-C3), Adafruit SSD1306/GFX, ESP_I2S
**Desktop:** Python 3.10+ · faster-whisper (STT) · pyttsx3 (TTS) · noisereduce + scipy (DSP) · pyserial · pyautogui / pygetwindow / pyperclip / pycaw · Ollama Cloud (MiniMax M3)

---

## 🤝 Contributing

Fork, branch, and open a PR. New tools are the easiest entry point — add one module under `desktop/tools/` and register it in `tools/__init__.py`.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**Knoc8** — the foundation for future robotics, embedded AI devices, and intelligent automation.

⭐ Star this repo if you find it useful!

</div>
