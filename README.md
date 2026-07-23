<div align="center">

# 🤖 Knoc8 Desktop Agent

**A voice-controlled AI operating agent for your PC — powered by an ESP32 and an LLM.**

*Not a chatbot. A desktop companion that listens, plans, and executes.*

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-Arduino-E7352C?logo=espressif&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-MiniMax%20M3%20·%20Ollama%20Cloud-black)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

Speak a command into the ESP32 mic. Knoc8 transcribes it, reasons about it with an LLM, plans the steps, executes them on your desktop — terminal, apps, browser, files, windows — and speaks the result back through your PC speakers while the ESP32's OLED shows what it's doing.

> 🗣️ *"Create a React project."* → terminal opens → `npm create vite` → packages installed → editor opens → dev server running → 🔊 *"Task completed successfully. What would you like me to do next, sir?"*

---

## ✨ Features

| | |
|---|---|
| 🎙️ **Hands-free wake word** | Say **"Hey Agent"** and speak — no buttons |
| 🧠 **LLM reasoning** | MiniMax M3 via Ollama Cloud — swappable with one env var |
| 📋 **Multi-step planning** | Complex requests become validated, ordered tool plans |
| 🖥️ **10 desktop tools** | Terminal, apps, browser, keyboard, mouse, clipboard, files, windows, system, notifications |
| 🔊 **Spoken responses** | Offline TTS through the PC speakers |
| 📟 **OLED status display** | IDLE · LISTEN · THINK · WORKING · SPEAK |
| 🛡️ **Safety gate** | Dangerous actions (delete, shutdown, risky commands) require typed confirmation |
| 💾 **Persistent memory** | *"My current project is Karigar"* — remembered across restarts |
| ⌨️ **Text mode** | No ESP32 connected? Full agent works from a console REPL |

---

## 🔁 How It Works

```
 🎙️ ESP32 streams mic audio continuously ──► USB Serial (COM16 @ 921600)
        │                                                          │
        │                                       Wake word detector hears "Hey Agent"
        │                                                          │
        │                                       Silence detection captures the command
        │                                                          │
        │                                          Whisper Speech-to-Text
        │                                                          │
        │                                          LLM plans tool calls (JSON)
        │                                                          │
        │                                          Planner validates & executes
        │                                                          │
 📟 OLED mirrors status ◄── USB Serial      🔊 PC speakers ◄── TTS reply
```

**Strict separation of concerns:** the ESP32 is hardware only — mic, speaker, OLED, serial. All AI runs on the PC. The LLM never executes anything directly; it proposes JSON tool calls that Python validates against a registry before running:

```json
{
  "reply": "Opening Chrome, sir.",
  "plan": [
    { "tool": "application", "action": "open", "args": { "name": "chrome" } }
  ]
}
```

---

## 📁 Project Structure

```
knoc8-desktop/
├── esp32/
│   └── firmware.ino          # I2S mic streaming, OLED status, serial protocol
└── desktop/
    ├── main.py               # Entry point — hardware loop + text-mode REPL
    ├── serial_manager.py     # COM16 auto-detect, framed audio protocol
    ├── wake_word.py          # "Hey Agent" detection + silence-based capture
    ├── speech_to_text.py     # faster-whisper STT
    ├── text_to_speech.py     # Offline TTS → 16 kHz PCM
    ├── llm.py                # LLMProvider → OllamaCloudProvider
    ├── planner.py            # JSON plans, validation, safety, summaries
    ├── memory.py             # Persistent facts + conversation history
    ├── logger.py             # Console + rotating file logs
    ├── config.py             # All settings in one place
    └── tools/                # One module per capability
        ├── terminal.py       ├── applications.py   ├── browser.py
        ├── keyboard.py       ├── mouse.py          ├── clipboard.py
        ├── filesystem.py     ├── windows.py        ├── notification.py
        └── system.py
```

Every module has one responsibility. Adding a tool = one new file + one registry line.

---

## 🔌 Hardware

| Part | Purpose |
|---|---|
| ESP32-C6 dev board | The voice interface |
| INMP441 | I2S microphone |
| SSD1306 128×64 OLED | Status display (I2C) |

### Wiring (ESP32-C6)

| Component | Pin | ESP32-C6 GPIO |
|---|---|---|
| INMP441 | SCK / WS / SD | 4 / 5 / 2 |
| INMP441 | L/R | GND |
| SSD1306 | SDA / SCL | 6 / 7 |

> ⚠️ Never wire anything to the flash pins (labeled CLK/CMD/SD0-SD3 on some boards) — it corrupts flash access.

Mic audio: **16 kHz · 16-bit · mono PCM** over serial at **921600 baud**. Spoken replies play through the **PC speakers**.

---

## 🚀 Quick Start

### 1 — Flash the ESP32

1. Open `esp32/firmware.ino` in Arduino IDE
2. Install **Adafruit SSD1306** + **Adafruit GFX Library** from Library Manager
3. Select board **ESP32C6 Dev Module** (needs Arduino-ESP32 core 3.x) and upload at speed **115200**

### 2 — Set up the desktop app

```bash
git clone https://github.com/<your-username>/knoc8-desktop.git
cd knoc8-desktop/desktop

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### 3 — Configure

Create `desktop/.env` (git-ignored — never commit your key):

```env
OLLAMA_API_KEY=your-ollama-cloud-api-key
KNOC8_SERIAL_PORT=COM16
```

### 4 — Run

```bash
python main.py
```

- **ESP32 connected** → hardware mode: say **"Hey Agent"**, then speak your command
- **No ESP32** → text mode: type commands into the console, same brain

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_API_KEY` | — | Ollama Cloud API key (**required**) |
| `KNOC8_SERIAL_PORT` | `COM16` | ESP32 serial port |
| `KNOC8_SERIAL_BAUD` | `921600` | Serial speed |
| `KNOC8_LLM_MODEL` | `minimax-m3` | Any Ollama Cloud model |
| `KNOC8_WHISPER_MODEL` | `base` | Whisper size: `tiny` / `base` / `small`... |
| `KNOC8_WAKE_WORD` | `hey agent` | The wake phrase — change it to anything |

Switching LLMs is one env var. Switching providers is one new class implementing `LLMProvider` — nothing else in the codebase references Ollama.

---

## 🗣️ Example Commands

| Say this | Knoc8 does |
|---|---|
| *"Open Cursor."* | Launches the app and confirms |
| *"Create a React project."* | `npm create vite` → install → editor → dev server |
| *"Open Chrome and search Python decorators."* | Browser → Google search |
| *"Run my React project."* | Navigates → `npm run dev` → reads output → reports |
| *"Search YouTube for transformer tutorials."* | Opens YouTube results |
| *"Set volume to 40."* | System volume → 40% |
| *"Remember that my current project is Karigar."* | Stored permanently |
| *"Delete the old backup folder."* | ⚠️ Asks for confirmation first |

---

## 🛡️ Safety

- The LLM **only proposes** tool calls — Python validates every step against the registry before execution
- Destructive actions always require a typed `yes`: file/folder deletion, shutdown, restart, and terminal commands matching dangerous patterns (`rm`, `del`, `format`, `diskpart`, `reg add/delete`, ...)
- A failing step stops the rest of the plan
- Every command, transcript, LLM response, and result is logged to `desktop/logs/`
- `pyautogui` failsafe: slam the mouse into a screen corner to abort automation instantly

---

## 📡 Serial Protocol

```
PC → ESP32   STATUS:<IDLE|LISTENING|THINKING|EXECUTING|SPEAKING>

ESP32 → PC   READY
             CHUNK:<n> + n bytes of raw PCM (continuous mic stream)
```

Chunk-framing keeps binary audio from ever corrupting line parsing, and the protocol is trivially extendable with new message types.

---

## 🗺️ Roadmap

- [x] Wake word detection (hands-free — *"Hey Agent"*)
- [ ] Camera + computer vision
- [ ] Face recognition
- [ ] Local LLM support
- [ ] Home automation & IoT control
- [ ] Robot control
- [ ] Plugin system

All possible without redesigning the architecture — the ESP32 stays a thin hardware interface and the tool registry just grows.

---

## 🤝 Contributing

Contributions are welcome! Fork the repo, create a feature branch, and open a pull request. New tools are the easiest entry point: add one module under `desktop/tools/` and register it in `tools/__init__.py`.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**Knoc8** — the foundation for future robotics, embedded AI devices, and intelligent automation.

⭐ Star this repo if you find it useful!

</div>
