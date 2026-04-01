import os
import sys
import time
import requests
import base64
import threading
import json
import uuid
import subprocess
from io import BytesIO
from typing import List, Dict
from PIL import ImageGrab, Image

import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk

def resource_path(relative_path):
    try:
        # PyInstaller создает временную папку _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    import speech_recognition as sr
    HAS_STT = True
except ImportError:
    HAS_STT = False

try:
    import pystray
    from pystray import MenuItem as item
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

PROXY_URL = os.environ.get("GAS_PROXY_URL", "https://script.google.com/macros/s/AKfycbwdJJeUVKPqALl3bf8wMmySgJPE8wXdNhecdgWIa72gTpbax1rrNSnkangMSyDDwNrI/exec")

ctk.set_appearance_mode("dark")

if HAS_DND:
    class BaseTkClass(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class BaseTkClass(ctk.CTk):
        pass

class LocalAIAssistant:
    def __init__(self):
        self.local_knowledge: str = ""
        self.chats = {} 
        self.current_chat_id = None
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        self.session = requests.Session()
        
        # Храним историю в папке пользователя, чтобы EXE всегда имел доступ на запись
        self.history_file = os.path.join(os.path.expanduser("~"), "aura_history.json")
        
        self.system_prompt = "Ты — полезный ИИ-ассистент по имени Аура. Всегда отвечай на русском языке. Будь точна, профессиональна и лаконична."

    def create_chat(self, name="Новый чат"):
        chat_id = str(uuid.uuid4())
        self.chats[chat_id] = {"name": name, "history": []}
        self.current_chat_id = chat_id
        return chat_id

    def delete_chat(self, chat_id):
        if chat_id in self.chats:
            del self.chats[chat_id]
        if not self.chats:
            self.create_chat()
        elif self.current_chat_id == chat_id:
            self.current_chat_id = list(self.chats.keys())[0]

    def rename_chat(self, chat_id, new_name):
        if chat_id in self.chats:
            self.chats[chat_id]["name"] = new_name

    def switch_chat(self, chat_id):
        if chat_id in self.chats:
            self.current_chat_id = chat_id

    def get_current_history(self) -> List[Dict]:
        if not self.current_chat_id or self.current_chat_id not in self.chats:
            self.create_chat()
        return self.chats[self.current_chat_id]["history"]

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.chats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения истории: {e}")

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.chats = data
                        if self.chats:
                            self.current_chat_id = list(self.chats.keys())[0]
            except Exception: pass
        if not self.chats:
            self.create_chat()

    def _send_to_proxy(self, api_url: str, payload: dict) -> dict:
        proxy_payload = {"url": api_url, "payload": payload}
        try:
            response = self.session.post(PROXY_URL, json=proxy_payload, timeout=35)
            return response.json()
        except Exception as e:
            return {"error": f"Сетевая ошибка: {e}"}

    def _send_with_retry(self, api_url: str, payload: dict, max_retries=2) -> dict:
        for attempt in range(max_retries):
            response_data = self._send_to_proxy(api_url, payload)
            if "error" in response_data:
                err_msg = str(response_data["error"])
                if "Quota" in err_msg or "429" in err_msg:
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue
            return response_data
        return response_data

    def _extract_text_from_response(self, response_data: dict) -> str:
        if "error" in response_data: 
            err = response_data["error"]
            return f"❌ Ошибка: {err.get('message', str(err))}" if isinstance(err, dict) else str(err)
        try: 
            return response_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError): 
            return f"❌ Не удалось получить ответ."

    def ask(self, question: str, use_web_search: bool = False) -> str:
        history = self.get_current_history()
        search_context = ""
        if use_web_search and HAS_DDGS:
            try:
                results = DDGS().text(question, max_results=3, region='ru-ru')
                if results:
                    search_context = "АКТУАЛЬНЫЕ ДАННЫЕ ИЗ СЕТИ:\n" + "\n".join([r['body'] for r in results]) + "\n\n"
            except Exception: pass

        prompt_to_send = search_context + question
        history.append({"role": "user", "parts": [{"text": question}]})
        
        api_history = list(history)
        api_history[-1] = {"role": "user", "parts": [{"text": prompt_to_send}]}
        
        payload = {
            "contents": api_history,
            "system_instruction": {"parts": [{"text": self.system_prompt}]}
        }
        
        response_data = self._send_with_retry(self.gemini_endpoint, payload)
        answer_text = self._extract_text_from_response(response_data)
        
        if not answer_text.startswith("❌"):
            history.append({"role": "model", "parts": [{"text": answer_text}]})
        return answer_text

    def analyze_screen(self, prompt: str) -> str:
        try:
            screenshot = ImageGrab.grab()
            screenshot.thumbnail((1024, 768))
            buffered = BytesIO()
            screenshot.save(buffered, format="JPEG", quality=60)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            payload = {
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}]}],
                "system_instruction": {"parts": [{"text": self.system_prompt}]}
            }
            response_data = self._send_with_retry(self.gemini_endpoint, payload)
            return self._extract_text_from_response(response_data)
        except Exception as e: return f"❌ Ошибка захвата экрана: {e}"

    def analyze_image(self, image_path: str, prompt: str) -> str:
        try:
            img = Image.open(image_path)
            if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
            img.thumbnail((1024, 768))
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=60)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            payload = {
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}]}],
                "system_instruction": {"parts": [{"text": self.system_prompt}]}
            }
            response_data = self._send_with_retry(self.gemini_endpoint, payload)
            return self._extract_text_from_response(response_data)
        except Exception as e: return f"❌ Ошибка обработки картинки: {e}"

    def load_document(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                self.local_knowledge = file.read()
            return True
        except Exception: return False
            
    def ask_about_document(self, question: str) -> str:
        if not self.local_knowledge: return "Сначала загрузи текстовый файл!"
        system_instruction = self.system_prompt + " Отвечай СТРОГО на основе предоставленного документа."
        prompt_text = f"--- ТЕКСТ ДОКУМЕНТА ---\n{self.local_knowledge}\n--- КОНЕЦ ---\n\nВопрос: {question}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "system_instruction": {"parts": [{"text": system_instruction}]}
        }
        response_data = self._send_with_retry(self.gemini_endpoint, payload)
        return self._extract_text_from_response(response_data)

class AuraApp(BaseTkClass): 
    def __init__(self):
        super().__init__()
        
        self.title("Aura AI")
        self.geometry("1200x800")
        self.minsize(900, 650)
        
        # Премиальная цветовая схема
        self.bg_color = "#000000"         
        self.sidebar_color = "#09090b"    
        self.input_bg_color = "#18181b"   
        self.accent_color = "#3b82f6"     
        self.accent_hover = "#2563eb"     
        self.text_main = "#fafafa"        
        self.text_muted = "#a1a1aa"       
        
        self.configure(fg_color=self.bg_color)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.assistant = LocalAIAssistant()
        self.assistant.load_history()
        self.last_parsed_code = "" 
        
        self.personas = {
            "🤖 Базовый ИИ": "Ты — полезный ИИ-ассистент. Всегда отвечай на русском языке.",
            "👨‍🏫 Учитель": "Ты — мудрый наставник. Объясняй всё максимально наглядно и просто.",
            "💻 Senior Coder": "Ты — опытный разработчик. Пиши только чистый, оптимизированный код.",
            "🌍 Переводчик": "Ты — мастер перевода. Качественно переводи текст на английский или русский."
        }
        
        if HAS_KEYBOARD:
            keyboard.add_hotkey('ctrl+shift+space', self.toggle_window)
            self.is_hidden = False

        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.handle_file_drop)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- САЙДБАР (ЛЕВОЕ МЕНЮ) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color=self.sidebar_color)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(3, weight=1) 
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="✨ AURA AI", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=self.text_main)
        self.logo_label.grid(row=0, column=0, pady=(40, 30), padx=25, sticky="w")

        self.btn_new_chat = ctk.CTkButton(self.sidebar_frame, text="+ Новый диалог", 
                                          fg_color="transparent", border_width=1, border_color="#27272a", 
                                          hover_color="#18181b", text_color=self.text_main, height=45,
                                          command=self.action_new_chat, font=ctk.CTkFont(family="Segoe UI", size=14))
        self.btn_new_chat.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.persona_var = ctk.StringVar(value="🤖 Базовый ИИ")
        self.persona_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=list(self.personas.keys()), variable=self.persona_var,
                                              fg_color="#18181b", button_color="#18181b", button_hover_color="#27272a",
                                              command=self.action_change_persona, font=ctk.CTkFont(family="Segoe UI", size=13), height=35)
        self.persona_menu.grid(row=2, column=0, padx=20, pady=(25, 10), sticky="ew")

        self.chat_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.chat_list_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)

        # Кнопки инструментов
        self.tools_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.tools_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=20)

        self.web_search_var = ctk.BooleanVar(value=False)
        self.switch_web = ctk.CTkSwitch(self.tools_frame, text="Поиск в интернете", variable=self.web_search_var, 
                                        progress_color=self.accent_color, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.switch_web.pack(pady=10, fill="x")
        if not HAS_DDGS: self.switch_web.configure(state="disabled")

        self.btn_run_code = ctk.CTkButton(self.tools_frame, text="▶ Запустить Python", state="disabled", 
                                          fg_color="#22c55e", hover_color="#16a34a", text_color="white",
                                          command=self.action_run_code, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), height=35)
        self.btn_run_code.pack(pady=5, fill="x")

        self.mini_tools_frame = ctk.CTkFrame(self.tools_frame, fg_color="transparent")
        self.mini_tools_frame.pack(fill="x", pady=5)
        self.mini_tools_frame.grid_columnconfigure((0,1), weight=1)

        self.btn_screen = ctk.CTkButton(self.mini_tools_frame, text="👁 Экран", fg_color="#18181b", hover_color="#27272a", 
                                        command=self.action_analyze_screen, font=ctk.CTkFont(family="Segoe UI", size=12), height=32)
        self.btn_screen.grid(row=0, column=0, padx=(0,5), sticky="ew")

        self.btn_doc = ctk.CTkButton(self.mini_tools_frame, text="📄 Файл", fg_color="#18181b", hover_color="#27272a", 
                                     command=self.action_load_doc, font=ctk.CTkFont(family="Segoe UI", size=12), height=32)
        self.btn_doc.grid(row=0, column=1, padx=(5,0), sticky="ew")
        
        self.status_label = ctk.CTkLabel(self.tools_frame, text="Aura AI готова", text_color=self.text_muted, font=ctk.CTkFont(family="Segoe UI", size=11))
        self.status_label.pack(side="bottom", pady=(15, 0))

        # --- ЦЕНТРАЛЬНОЕ ОКНО ---
        self.chat_frame = ctk.CTkFrame(self, fg_color=self.bg_color)
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_box = ctk.CTkTextbox(self.chat_frame, wrap="word", fg_color="transparent", 
                                       text_color=self.text_main, font=ctk.CTkFont(family="Segoe UI", size=16)) 
        self.chat_box.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 25))
        
        # Магия стилизации через ядро Tkinter (для жирности и отступов)
        tk_textbox = self.chat_box._textbox
        tk_textbox.tag_configure("user_icon", font=("Segoe UI", 14, "bold"), foreground="#38bdf8", spacing1=40, spacing3=12)
        tk_textbox.tag_configure("ai_icon", font=("Segoe UI", 14, "bold"), foreground="#a78bfa", spacing1=40, spacing3=12)
        tk_textbox.tag_configure("sys_icon", font=("Segoe UI", 12, "italic"), foreground="#f472b6", spacing1=25, spacing3=12)
        tk_textbox.tag_configure("normal_text", font=("Segoe UI", 13), foreground="#e4e4e7", spacing1=2, spacing3=2)
        tk_textbox.tag_configure("bold_text", font=("Segoe UI", 13, "bold"), foreground="#ffffff")
        tk_textbox.tag_configure("code", font=("Consolas", 13), background="#111113", foreground="#4ade80", 
                                 spacing1=15, spacing3=15, lmargin1=30, lmargin2=30, rmargin=30)

        # Контекстное меню для копирования
        self.context_menu = tk.Menu(self, tearoff=False, bg="#18181b", fg="#fafafa", activebackground="#3b82f6", borderwidth=0)
        self.context_menu.add_command(label="📋 Копировать", command=self.copy_selection)
        self.context_menu.add_command(label="📑 Копировать всё", command=self.copy_all)
        self.chat_box._textbox.bind("<Button-3>", self.show_context_menu)

        # --- ПАНЕЛЬ ВВОДА ---
        self.input_container = ctk.CTkFrame(self.chat_frame, fg_color=self.input_bg_color, corner_radius=30)
        self.input_container.grid(row=1, column=0, sticky="ew", padx=60, pady=(0, 20))
        self.input_container.grid_columnconfigure(2, weight=1) 

        self.btn_mic = ctk.CTkButton(self.input_container, text="🎙", width=50, height=50, fg_color="transparent", hover_color="#27272a", command=self.action_record_voice, font=ctk.CTkFont(size=22))
        self.btn_mic.grid(row=0, column=0, padx=(15, 0), pady=8)
        if not HAS_STT: self.btn_mic.configure(state="disabled")

        self.btn_image = ctk.CTkButton(self.input_container, text="📎", width=50, height=50, fg_color="transparent", hover_color="#27272a", command=self.action_upload_image, font=ctk.CTkFont(size=22))
        self.btn_image.grid(row=0, column=1, padx=(5, 5), pady=8)

        self.entry = ctk.CTkTextbox(self.input_container, height=60, fg_color="transparent", text_color=self.text_main, font=ctk.CTkFont(family="Segoe UI", size=15), wrap="word")
        self.entry.grid(row=0, column=2, sticky="ew", padx=10, pady=12)
        
        self.entry.bind("<Return>", self._on_enter_pressed)
        self.entry.bind("<<Paste>>", self._paste_text) 
        self.entry.bind("<Control-v>", self._paste_text) 

        self.btn_send = ctk.CTkButton(self.input_container, text="➤", width=50, height=50, corner_radius=25, 
                                      fg_color=self.accent_color, hover_color=self.accent_hover, text_color="white",
                                      command=self.action_send_message, font=ctk.CTkFont(size=22))
        self.btn_send.grid(row=0, column=3, padx=(10, 15), pady=8)

        self.render_chat_list()
        self.reload_chat_ui()

    # --- ЛОГИКА ИНТЕРФЕЙСА ---
    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_selection(self):
        try:
            selected = self.chat_box._textbox.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected)
        except tk.TclError: pass

    def copy_all(self):
        text = self.chat_box.get("0.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)

    def _on_enter_pressed(self, event):
        if event.state & 0x0001: return None
        self.action_send_message()
        return "break"

    def _paste_text(self, event):
        try:
            text = self.clipboard_get()
            self.entry.insert("insert", text)
        except Exception: pass
        return "break"

    def action_change_persona(self, selected_role):
        new_prompt = self.personas[selected_role]
        self.assistant.system_prompt = new_prompt
        self.append_to_chat(f"Режим изменен: {selected_role}", "Система")

    def handle_file_drop(self, event):
        filepaths = self.tk.splitlist(event.data)
        if not filepaths: return
        filepath = filepaths[0]
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
            user_text = self.entry.get("0.0", "end").strip()
            prompt = user_text if user_text else "Проанализируй это изображение."
            self.entry.delete("0.0", "end")
            self.append_to_chat(f"📎 Анализ файла: {os.path.basename(filepath)}\n{prompt}", "Вы")
            self.set_loading_state(True)
            threading.Thread(target=self._thread_analyze_image, args=(filepath, prompt), daemon=True).start()
        elif ext in ['.txt', '.md', '.py', '.json', '.csv', '.html', '.js', '.log']:
            if self.assistant.load_document(filepath):
                self.append_to_chat(f"Документ успешно загружен: {os.path.basename(filepath)}", "Система")
            else: self.append_to_chat("Не удалось открыть файл.", "Система")

    def render_chat_list(self):
        for widget in self.chat_list_frame.winfo_children(): widget.destroy()
        for chat_id, chat_data in self.assistant.chats.items():
            row = ctk.CTkFrame(self.chat_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)
            is_active = chat_id == self.assistant.current_chat_id
            color = "#18181b" if is_active else "transparent"
            btn_name = ctk.CTkButton(row, text=chat_data["name"], fg_color=color, hover_color="#18181b", anchor="w", 
                                     text_color=self.text_main if is_active else self.text_muted,
                                     font=ctk.CTkFont(family="Segoe UI", size=13),
                                     command=lambda cid=chat_id: self.action_switch_chat(cid))
            btn_name.pack(side="left", fill="x", expand=True, padx=(0, 2))
            btn_rename = ctk.CTkButton(row, text="✎", width=35, fg_color=color, hover_color="#27272a", text_color=self.text_muted, command=lambda cid=chat_id: self.action_rename_chat(cid))
            btn_rename.pack(side="left", padx=1)
            btn_del = ctk.CTkButton(row, text="×", width=35, fg_color=color, hover_color="#ef4444", text_color=self.text_muted, command=lambda cid=chat_id: self.action_delete_chat(cid))
            btn_del.pack(side="left")

    def reload_chat_ui(self):
        self.chat_box.configure(state="normal")
        self.chat_box.delete("0.0", "end")
        self.btn_run_code.configure(state="disabled") 
        self.chat_box.insert("0.0", "✨ Приветствую, Влад! Aura AI готова к работе.\n\n", "ai_icon")
        for msg in self.assistant.get_current_history():
            role = "Вы" if msg["role"] == "user" else "Aura"
            self._insert_formatted_text(msg["parts"][0]["text"], role)
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def action_new_chat(self):
        self.assistant.create_chat()
        self.render_chat_list()
        self.reload_chat_ui()

    def action_switch_chat(self, chat_id):
        self.assistant.switch_chat(chat_id)
        self.render_chat_list()
        self.reload_chat_ui()

    def action_delete_chat(self, chat_id):
        self.assistant.delete_chat(chat_id)
        self.render_chat_list()
        self.reload_chat_ui()

    def action_rename_chat(self, chat_id):
        dialog = ctk.CTkInputDialog(text="Введите название чата:", title="Переименование")
        new_name = dialog.get_input()
        if new_name and new_name.strip():
            self.assistant.rename_chat(chat_id, new_name.strip()[:30])
            self.render_chat_list()

    def toggle_window(self):
        if self.state() == "iconic" or not self.winfo_viewable() or self.is_hidden:
            self.show_window_gui()
        else:
            self.withdraw()
            self.is_hidden = True

    def show_window_gui(self):
        self.deiconify()
        self.attributes('-topmost', True)
        self.attributes('-topmost', False)
        self.focus_force()
        self.entry.focus()
        self.is_hidden = False

    def on_closing(self):
        if HAS_TRAY:
            self.withdraw()
            self.is_hidden = True
            self.assistant.save_history() 
            image = Image.new('RGB', (64, 64), color=(59, 130, 246))
            menu = (item('Развернуть Aura AI', self.tray_open), item('Выйти из приложения', self.tray_quit))
            self.tray_icon = pystray.Icon("Aura", image, "Aura AI", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        else:
            self.assistant.save_history()
            self.destroy()

    def tray_open(self, icon, item):
        icon.stop() 
        self.after(0, self.show_window_gui) 

    def tray_quit(self, icon, item):
        icon.stop()
        self.assistant.save_history()
        os._exit(0) 

    def _insert_formatted_text(self, text: str, sender: str):
        if sender == "Система":
            self.chat_box.insert("end", f"⚙️ {text}\n", ("sys_icon"))
            return
        icon_tag = "user_icon" if sender == "Вы" else "ai_icon"
        name = "ВЫ" if sender == "Вы" else "AURA"
        self.chat_box.insert("end", f"{name}\n", icon_tag)
        parts = text.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1: 
                code_lines = part.split("\n", 1)
                if len(code_lines) > 1:
                    lang = code_lines[0].strip().lower()
                    clean_code = code_lines[1]
                    if lang in ["python", "py", ""]:
                        self.last_parsed_code = clean_code.strip()
                        self.btn_run_code.configure(state="normal")
                else: clean_code = code_lines[0]
                self.chat_box.insert("end", f"\n{clean_code}\n", "code")
            else:
                bold_parts = part.split("**")
                for j, b_part in enumerate(bold_parts):
                    if j % 2 == 1: self.chat_box.insert("end", b_part, "bold_text")
                    else: self.chat_box.insert("end", b_part, "normal_text")
        self.chat_box.insert("end", "\n") 

    def action_run_code(self):
        if not self.last_parsed_code: return
        self.append_to_chat("Запуск скрипта...", "Система")
        self.btn_run_code.configure(state="disabled") 
        def run_it():
            try:
                temp_py = os.path.join(os.path.expanduser("~"), "aura_temp_exec.py")
                with open(temp_py, "w", encoding="utf-8") as f:
                    f.write(self.last_parsed_code)
                result = subprocess.run(["python", temp_py], capture_output=True, text=True, timeout=20)
                out, err = result.stdout.strip(), result.stderr.strip()
                if out: self.after(0, self.append_to_chat, f"Результат выполнения:\n{out}", "Система")
                if err: self.after(0, self.append_to_chat, f"Обнаружены ошибки:\n{err}", "Система")
                if not out and not err: self.after(0, self.append_to_chat, "Скрипт выполнен успешно.", "Система")
            except Exception as e: self.after(0, self.append_to_chat, f"Ошибка исполнения: {e}", "Система")
        threading.Thread(target=run_it, daemon=True).start()

    def append_to_chat(self, text: str, sender: str):
        self.chat_box.configure(state="normal")
        self._insert_formatted_text(text, sender)
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def set_loading_state(self, is_loading: bool):
        state = "disabled" if is_loading else "normal"
        self.btn_send.configure(state=state)
        self.btn_image.configure(state=state)
        if HAS_STT: self.btn_mic.configure(state=state)
        self.entry.configure(state=state)
        self.btn_screen.configure(state=state)
        self.btn_doc.configure(state=state)
        self.btn_new_chat.configure(state=state)
        self.switch_web.configure(state="disabled" if not HAS_DDGS else state)
        self.persona_menu.configure(state=state)
        for widget in self.chat_list_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkButton): child.configure(state=state)
        if not is_loading: self.entry.focus()

    def action_record_voice(self):
        self.entry.delete("0.0", "end")
        self.entry.insert("0.0", "Слушаю вас...")
        self.set_loading_state(True)
        threading.Thread(target=self._thread_record_voice, daemon=True).start()

    def _thread_record_voice(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio, language="ru-RU")
                self.after(0, self._on_voice_recognized, text)
        except Exception: self.after(0, self._on_voice_recognized, f"Не удалось разобрать.")

    def _on_voice_recognized(self, text):
        self.set_loading_state(False)
        self.entry.delete("0.0", "end")
        if not text.startswith("Не удалось"):
            self.entry.insert("0.0", text)
            self.action_send_message() 

    def speak_text(self, text: str):
        if not HAS_TTS: return
        def run_tts():
            try:
                engine = pyttsx3.init()
                clean_text = text.replace("*", "").replace("```", "")
                engine.say(clean_text)
                engine.runAndWait()
            except Exception: pass
        threading.Thread(target=run_tts, daemon=True).start()

    def action_send_message(self):
        user_text = self.entry.get("0.0", "end").strip()
        if not user_text: return 
        self.entry.delete("0.0", "end")
        self.append_to_chat(user_text, "Вы")
        self.set_loading_state(True)
        use_web = self.web_search_var.get()
        threading.Thread(target=self._thread_ask, args=(user_text, use_web), daemon=True).start()

    def _thread_ask(self, user_text, use_web):
        if self.assistant.local_knowledge: response = self.assistant.ask_about_document(user_text)
        else: response = self.assistant.ask(user_text, use_web_search=use_web)
        self.after(0, self._on_response_received, response)

    def action_analyze_screen(self):
        self.append_to_chat("Анализирую происходящее на экране...", "Система")
        self.set_loading_state(True)
        threading.Thread(target=self._thread_analyze_screen, daemon=True).start()

    def _thread_analyze_screen(self):
        response = self.assistant.analyze_screen("Опиши экран подробно.")
        self.after(0, self._on_response_received, response)

    def action_upload_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if not filepath: return
        user_text = self.entry.get("0.0", "end").strip()
        prompt = user_text if user_text else "Что ты видишь на этой картинке?"
        self.entry.delete("0.0", "end")
        self.append_to_chat(f"📎 Файл: {os.path.basename(filepath)}\n{prompt}", "Вы")
        self.set_loading_state(True)
        threading.Thread(target=self._thread_analyze_image, args=(filepath, prompt), daemon=True).start()

    def _thread_analyze_image(self, filepath, prompt):
        response = self.assistant.analyze_image(filepath, prompt)
        self.after(0, self._on_response_received, response)

    def action_load_doc(self):
        filepath = filedialog.askopenfilename(filetypes=(("Текстовые файлы", "*.txt *.md *.py"), ("Все файлы", "*.*")))
        if filepath:
            if self.assistant.load_document(filepath):
                self.append_to_chat(f"Файл '{os.path.basename(filepath)}' загружен в активную память.", "Система")
            else: self.append_to_chat("Ошибка: не удалось прочитать файл.", "Система")

    def _on_response_received(self, response_text):
        self.append_to_chat(response_text, "Aura")
        self.set_loading_state(False)
        self.speak_text(response_text)

if __name__ == "__main__":
    app = AuraApp()
    app.mainloop()