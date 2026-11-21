import os
import re
import ctypes
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from PIL import ImageGrab
import keyboard
import pyttsx3
import google.generativeai as genai

# Windows DPI awareness adjustment
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# =====================================================================
# CONFIGURATION: Enter your Gemini API Key(s) below or set GEMINI_API_KEY
# =====================================================================
API_KEYS = [
    os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE"),
]
current_key_index = 0

# Choose your preferred Gemini model (e.g., "gemini-2.5-flash", "gemini-2.5-pro", "gemini-flash-latest")
SELECTED_MODEL = "gemini-2.5-flash"


def get_current_model():
    global current_key_index
    genai.configure(api_key=API_KEYS[current_key_index])
    return genai.GenerativeModel(SELECTED_MODEL)


def rotate_key():
    global current_key_index
    if len(API_KEYS) > 1:
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        return True
    return False


class ToastNotification:
    """Small auto-dismissing popup notification for silent OCR mode."""
    def __init__(self, parent, text):
        self.toast = tk.Toplevel(parent)
        self.toast.overrideredirect(True)
        self.toast.attributes("-topmost", True)
        self.toast.configure(bg="#313244")

        # Bottom-right corner above taskbar
        screen_w = self.toast.winfo_screenwidth()
        screen_h = self.toast.winfo_screenheight()
        w, h = 320, 80
        self.toast.geometry(f"{w}x{h}+{screen_w - w - 20}+{screen_h - h - 60}")

        lbl_title = tk.Label(
            self.toast, text="✓ Text Copied to Clipboard!",
            font=("Segoe UI", 10, "bold"), fg="#a6e3a1", bg="#313244"
        )
        lbl_title.pack(pady=(8, 2))

        preview = text.strip()[:60] + ("..." if len(text.strip()) > 60 else "")
        lbl_txt = tk.Label(
            self.toast, text=preview, font=("Segoe UI", 9),
            fg="#cdd6f4", bg="#313244", wraplength=300
        )
        lbl_txt.pack(padx=8)

        self.toast.after(3000, self.toast.destroy)


class SnippingOverlay:
    def __init__(self, mode, on_capture_callback):
        self.mode = mode
        self.on_capture = on_capture_callback
        self.root = tk.Toplevel()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.28)
        self.root.attributes("-topmost", True)
        self.root.config(cursor="cross")

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey15", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        outline_color = "#fab387" if mode == "ocr" else "#89b4fa"
        self.outline_color = outline_color
        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=self.outline_color, width=2
        )

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        self.root.destroy()
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        if (x2 - x1) > 15 and (y2 - y1) > 15:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            self.on_capture(img, self.mode)


class ResultWindow:
    def __init__(self, parent_root, image):
        self.parent = parent_root
        self.window = tk.Toplevel(parent_root)
        self.last_text = ""
        self.is_speaking = False
        self.tts_engine = None

        self.window.title("Ghost Watcher - AI Analysis")
        self.window.geometry("640x670")
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#1e1e2e")

        self.chat_session = None
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.header = tk.Label(
            self.window, text=f"Analyzing screen capture ({SELECTED_MODEL})...",
            font=("Segoe UI", 11, "bold"), bg="#181825", fg="#89b4fa", pady=8
        )
        self.header.pack(fill=tk.X)

        # Input bar
        bottom_frame = tk.Frame(self.window, bg="#1e1e2e")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=10)

        self.send_btn = tk.Button(
            bottom_frame, text="Send", font=("Segoe UI", 10, "bold"),
            bg="#89b4fa", fg="#11111b", width=7, relief=tk.FLAT, command=self.send_followup
        )
        self.send_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.entry = tk.Entry(
            bottom_frame, font=("Segoe UI", 11),
            bg="#313244", fg="#ffffff", insertbackground="white", relief=tk.FLAT
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda e: self.send_followup())

        # Action toolbar
        toolbar = tk.Frame(self.window, bg="#1e1e2e")
        toolbar.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 6))

        self.btn_copy = tk.Button(
            toolbar, text="📋 Copy to Clipboard", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg="#cdd6f4", relief=tk.FLAT, padx=10, pady=4, command=self.copy_to_clipboard
        )
        self.btn_copy.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_tts = tk.Button(
            toolbar, text="🔊 Read Aloud", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg="#cdd6f4", relief=tk.FLAT, padx=10, pady=4, command=self.toggle_speech
        )
        self.btn_tts.pack(side=tk.LEFT)

        # Output text area
        self.text_box = scrolledtext.ScrolledText(
            self.window, wrap=tk.WORD, bg="#11111b", fg="#cdd6f4",
            font=("Segoe UI", 11), padx=14, pady=14, relief=tk.FLAT, insertbackground="white"
        )
        self.text_box.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(10, 6))
        self.text_box.tag_config("rtl", justify="right")
        self.text_box.tag_config("ltr", justify="left")
        self.text_box.tag_config("user", foreground="#89b4fa", justify="left")
        self.text_box.tag_config("error", foreground="#f38ba8", justify="left")

        threading.Thread(target=self._process_image, args=(image,), daemon=True).start()

    def append_message(self, sender, text, align_tag):
        self.text_box.config(state="normal")
        self.text_box.insert(tk.END, f"{sender}:\n{text}\n\n", (align_tag,))
        self.text_box.see(tk.END)
        self.text_box.config(state="disabled")

    def copy_to_clipboard(self):
        if self.last_text:
            self.window.clipboard_clear()
            self.window.clipboard_append(self.last_text)
            self.btn_copy.config(text="✓ Copied!", bg="#a6e3a1", fg="#11111b")
            self.window.after(2000, lambda: self.btn_copy.config(text="📋 Copy to Clipboard", bg="#313244", fg="#cdd6f4"))

    def toggle_speech(self):
        if self.is_speaking:
            self.is_speaking = False
            if self.tts_engine:
                try:
                    self.tts_engine.stop()
                except Exception:
                    pass
            self.btn_tts.config(text="🔊 Read Aloud", bg="#313244", fg="#cdd6f4")
            return

        if not self.last_text:
            return

        self.is_speaking = True
        self.btn_tts.config(text="⏹ Stop Reading", bg="#f38ba8", fg="#11111b")

        def _speak_worker():
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 160)
                clean_speech = re.sub(r'[^\w\s\u0590-\u05FF]', ' ', self.last_text)
                self.tts_engine.say(clean_speech)
                self.tts_engine.runAndWait()
            except Exception:
                pass
            finally:
                self.is_speaking = False
                self.window.after(0, lambda: self.btn_tts.config(text="🔊 Read Aloud", bg="#313244", fg="#cdd6f4"))

        threading.Thread(target=_speak_worker, daemon=True).start()

    def _process_image(self, image):
        prompt = """
Look at this captured screen area and respond accurately, concisely, and directly:
1. If there is a riddle or question - solve it immediately and clearly state the answer and explanation.
2. If there is a math problem or equation - solve it step-by-step.
3. If there is a code error - provide the exact fix immediately.
4. For anything else - answer directly and to the point.
(Do not use markdown asterisks ** in your response).
"""
        attempts = 0
        while attempts < max(1, len(API_KEYS)):
            try:
                model = get_current_model()
                self.chat_session = model.start_chat(history=[])
                response = self.chat_session.send_message([prompt, image])
                reply = response.text.replace("**", "").replace("###", "")
                self.last_text = reply

                has_hebrew = bool(re.search(r'[\u0590-\u05FF]', reply))
                tag = "rtl" if has_hebrew else "ltr"
                self.window.after(0, self._set_initial_reply, reply, tag)
                return
            except Exception as e:
                if "429" in str(e) and rotate_key():
                    attempts += 1
                    continue
                self.window.after(0, self._set_error, str(e))
                return

    def _set_initial_reply(self, reply, tag):
        self.header.config(text="Analysis Complete!", fg="#a6e3a1")
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.config(state="disabled")
        self.append_message("Gemini", reply, tag)
        self.entry.focus()

    def _set_error(self, err):
        self.header.config(text="API Error", fg="#f38ba8")
        self.append_message("Error", err, "error")

    def send_followup(self):
        user_msg = self.entry.get().strip()
        if not user_msg or not self.chat_session:
            return

        self.append_message("You", user_msg, "user")
        self.entry.delete(0, tk.END)
        self.send_btn.config(state="disabled", text="Thinking...")

        threading.Thread(target=self._query_followup, args=(user_msg,), daemon=True).start()

    def _query_followup(self, user_msg):
        try:
            instruction = f"{user_msg}\n(Do not use markdown asterisks ** in your response)"
            response = self.chat_session.send_message(instruction)
            reply = response.text.replace("**", "").replace("###", "")
            self.last_text = reply
            has_hebrew = bool(re.search(r'[\u0590-\u05FF]', reply))
            tag = "rtl" if has_hebrew else "ltr"
            self.window.after(0, self.append_message, "Gemini", reply, tag)
        except Exception as e:
            self.window.after(0, self.append_message, "Error", str(e), "error")
        finally:
            self.window.after(0, lambda: self.send_btn.config(state="normal", text="Send"))

    def on_close(self):
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception:
                pass
        self.chat_session = None
        self.window.destroy()


class GhostWatcherApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self._ensure_api_key_and_model()

        print("==================================================")
        print(f"  Ghost Watcher is running in background! ({SELECTED_MODEL})")
        print("  - AI Screen Analysis & Chat: Ctrl + Alt + S")
        print("  - Quick Silent OCR Copy:     Ctrl + Alt + C")
        print("==================================================")

        keyboard.add_hotkey("ctrl+alt+s", lambda: self.trigger_snipping("ask"))
        keyboard.add_hotkey("ctrl+alt+c", lambda: self.trigger_snipping("ocr"))

    def _ensure_api_key_and_model(self):
        global SELECTED_MODEL
        # Prompt user for API key on startup if not configured in code or env
        if not API_KEYS[0] or API_KEYS[0] == "YOUR_GEMINI_API_KEY_HERE":
            user_key = simpledialog.askstring(
                "Ghost Watcher Setup",
                "Enter your Google Gemini API Key:",
                show="*"
            )
            if user_key and user_key.strip():
                API_KEYS[0] = user_key.strip()
            else:
                messagebox.showwarning(
                    "Missing API Key",
                    "No API key provided. Please set GEMINI_API_KEY or edit API_KEYS in ghost_watcher.py."
                )

        # Prompt user to confirm or choose which Gemini model to use
        chosen_model = simpledialog.askstring(
            "Select Gemini Model",
            "Which Gemini model would you like to use?\n(e.g., gemini-2.5-flash, gemini-2.5-pro, gemini-flash-latest)",
            initialvalue=SELECTED_MODEL
        )
        if chosen_model and chosen_model.strip():
            SELECTED_MODEL = chosen_model.strip()

    def trigger_snipping(self, mode):
        self.root.after(0, lambda: SnippingOverlay(mode, self.on_captured))

    def on_captured(self, image, mode):
        if mode == "ask":
            self.root.after(0, lambda: ResultWindow(self.root, image))
        elif mode == "ocr":
            threading.Thread(target=self._ocr_fast_worker, args=(image,), daemon=True).start()

    def _ocr_fast_worker(self, image):
        prompt = "Extract the exact text shown in this image word-for-word. Do not add any explanations, introductions, or extra words."
        attempts = 0
        while attempts < max(1, len(API_KEYS)):
            try:
                model = get_current_model()
                response = model.generate_content([prompt, image])
                raw_text = response.text.strip()

                self.root.clipboard_clear()
                self.root.clipboard_append(raw_text)

                self.root.after(0, lambda: ToastNotification(self.root, raw_text))
                return
            except Exception as e:
                if "429" in str(e) and rotate_key():
                    attempts += 1
                    continue
                return

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = GhostWatcherApp()
    app.run()