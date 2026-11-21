# 👻 Ghost Watcher (`ghost-watcher`)

A lightweight Windows background assistant powered by the **Google Gemini API** (`google-generativeai`). Capture any region of your screen via global hotkeys to instantly solve problems, chat about what's on your screen, listen via Text-to-Speech, or silently extract text (OCR) straight to your clipboard.

---

## ✨ Features & Global Hotkeys

Ghost Watcher runs quietly in the background and listens for two global shortcuts:

* **`Ctrl + Alt + S` — AI Screen Analysis & Interactive Chat:**
  * Drag to select any area of your screen.
  * Opens an always-on-top dark window with instant AI analysis (solves math problems step-by-step, explains code errors, answers questions).
  * Supports follow-up chat messages, one-click clipboard copy, and **Read Aloud (TTS)**.
* **`Ctrl + Alt + C` — Silent Quick OCR:**
  * Drag to select any text on your screen (even from images, videos, or unselectable UI elements).
  * Extracts the exact text silently in the background, copies it straight to your clipboard, and displays a sleek non-intrusive toast notification.

---

## 🛠️ Requirements & Installation

* **OS:** Windows 10 / Windows 11
* **Python:** Python 3.8+
* **API Key:** A free or paid Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).

### Install Dependencies


pip install Pillow keyboard pyttsx3 google-generativeai
🚀 Configuration & Usage
Run the script:


python ghost_watcher.py
On startup, if no API key is configured, a popup dialog will ask for your Gemini API Key and allow you to choose your preferred model (e.g., gemini-2.5-flash, gemini-2.5-pro).

(Optional) You can also set the GEMINI_API_KEY environment variable or edit API_KEYS and SELECTED_MODEL directly at the top of ghost_watcher.py.

Press Ctrl + Alt + S or Ctrl + Alt + C anytime, anywhere on Windows to capture your screen (press Esc to cancel a capture).

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
