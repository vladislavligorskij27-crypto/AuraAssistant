import os
import json
import time
import requests
import base64
import threading
import sys
import itertools
from io import BytesIO
from typing import List, Dict, Optional
from PIL import ImageGrab, Image

PROXY_URL = os.environ.get("GAS_PROXY_URL", "https://script.google.com/macros/s/AKfycbwdJJeUVKPqALl3bf8wMmySgJPE8wXdNhecdgWIa72gTpbax1rrNSnkangMSyDDwNrI/exec")

if not PROXY_URL or PROXY_URL == "ТВОЙ_WEB_APP_URL_СЮДА":
    print("ВНИМАНИЕ: Не найден URL прокси! Скрипт не будет работать.")
    print("Убедись, что ты опубликовал Google Script и скопировал Web App URL.")


class Spinner:

    def __init__(self, message="Думаю..."):
        self.spinner = itertools.cycle(['-', '\\', '|', '/'])
        self.stop_running = threading.Event()
        self.message = message
        self.thread = threading.Thread(target=self.spin)

    def spin(self):
        while not self.stop_running.is_set():
            sys.stdout.write(f'\r[{next(self.spinner)}] {self.message}')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 5) + '\r')

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_running.set()
        self.thread.join()


class LocalAIAssistant:
    
    def __init__(self):
        self.local_knowledge: str = ""
        self.chat_history: List[Dict] = []
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        
        self.session = requests.Session()

    def _send_to_proxy(self, api_url: str, payload: dict, loading_msg: str = "Связываюсь с сервером...") -> dict:
        proxy_payload = {
            "url": api_url,
            "payload": payload
        }
        
        spinner = Spinner(loading_msg)
        spinner.start()
        
        try:
            start_time = time.time()
            response = self.session.post(PROXY_URL, json=proxy_payload)
            response.raise_for_status() 
            
            spinner.stop()
            elapsed = time.time() - start_time
            print(f"[✓] Ответ получен за {elapsed:.1f} сек.")
            
            return response.json()
        except Exception as e:
            spinner.stop()
            return {"error": f"Ошибка связи с прокси: {e}"}

    def _extract_text_from_response(self, response_data: dict) -> str:
        if "error" in response_data:
            return response_data["error"]
        try:
            return response_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return f"❌ Не удалось разобрать ответ ИИ: {response_data}"

    def ask(self, question: str) -> str:
        print(f"\nВопрос: {question}")
        self.chat_history.append({"role": "user", "parts": [{"text": question}]})
        
        payload = {"contents": self.chat_history}
        
        response_data = self._send_to_proxy(self.gemini_endpoint, payload, "Ассистент генерирует ответ...")
        answer_text = self._extract_text_from_response(response_data)
        
        if not answer_text.startswith("❌"):
            self.chat_history.append({"role": "model", "parts": [{"text": answer_text}]})
            
        return answer_text

    def analyze_screen(self, prompt: str = "Опиши, что ты видишь на этом экране") -> str:
        print("\n[Делаю скриншот...]")
        try:
            screenshot = ImageGrab.grab()
            screenshot.thumbnail((1024, 768)) 
            
            buffered = BytesIO()
            screenshot.save(buffered, format="JPEG", quality=60)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            print(f"Запрос: {prompt}")
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
                    ]
                }]
            }
            
            response_data = self._send_to_proxy(self.gemini_endpoint, payload, "Отправляю изображение ИИ...")
            return self._extract_text_from_response(response_data)
            
        except Exception as e:
            return f"❌ Ошибка при анализе экрана: {e}"

    def load_document(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                self.local_knowledge = file.read()
            print(f"\n[+] Документ '{filepath}' успешно загружен в память!")
            return True
        except FileNotFoundError:
            print(f"\n[-] Ошибка: Файл '{filepath}' не найден.")
            return False
            
    def ask_about_document(self, question: str) -> str:
        if not self.local_knowledge:
            return "Сначала загрузи документ с помощью load_document()!"
            
        print(f"\n[Ищу в локальной базе...] Вопрос: {question}")
        
        system_instruction = "Ты - умный ассистент. Твоя задача - ответить на вопрос пользователя, используя ТОЛЬКО предоставленный текст документа. Если ответа нет, скажи 'Я не нашел информации об этом в документе'."
        prompt_text = f"--- НАЧАЛО ДОКУМЕНТА ---\n{self.local_knowledge}\n--- КОНЕЦ ДОКУМЕНТА ---\n\nВопрос: {question}"
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "system_instruction": {"parts": [{"text": system_instruction}]}
        }
        
        response_data = self._send_to_proxy(self.gemini_endpoint, payload, "Анализирую документ...")
        return self._extract_text_from_response(response_data)


if __name__ == "__main__":
    test_file_name = "my_notes.txt"
    with open(test_file_name, "w", encoding="utf-8") as f:
        f.write("Секретная информация: Сервер базы данных находится по адресу 192.168.1.100. Пароль от админки: SuperSecret2026. Проект называется 'Aura'.")

    assistant = LocalAIAssistant()
    print("🤖 Ассистент запущен (Работает через Proxy)!")
    time.sleep(1)

    # ДЕМО 1
    answer1 = assistant.ask("Привет! Придумай короткое название для проекта десктопного ИИ-ассистента.")
    print(f"Ответ ИИ:\n{answer1}\n{'-'*40}")
    
    # ДЕМО 2
    assistant.load_document(test_file_name)
    answer2 = assistant.ask_about_document("Какой пароль от админки и как называется проект?")
    print(f"Ответ ИИ (по документу):\n{answer2}\n{'-'*40}")
    
    if os.path.exists(test_file_name):
         os.remove(test_file_name)