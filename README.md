✨ Aura AI Assistant

Современный десктопный ассистент на базе Google Gemini 2.5 Flash с премиальным Amoled-дизайном.

🚀 Основные возможности

🧠 Мультимодальность: Анализ экрана, обработка изображений и текстовых документов.

🎤 Голос: Голосовой ввод и озвучка ответов (Text-to-Speech).

🌐 Веб-поиск: Доступ к актуальной информации через DuckDuckGo.

▶️ Code Runner: Выполнение Python-кода, написанного ИИ, прямо в приложении.

🌗 Дизайн: Стильный Amoled Black интерфейс с Markdown-рендерингом и подсветкой кода.

📎 Удобство: Поддержка Drag-and-Drop для файлов и системная горячая клавиша Ctrl+Shift+Space.

👻 Трей: Сворачивание в системный лоток для фоновой работы.

🛠 Установка (для разработчиков)

Клонируйте репозиторий:

git clone [https://github.com/ВАШ_НИК/AuraAssistant.git](https://github.com/ВАШ_НИК/AuraAssistant.git)
cd AuraAssistant


Установите зависимости:

pip install -r requirements.txt


Настройте Proxy:
Установите переменную окружения GAS_PROXY_URL или замените её напрямую в коде aura_app.py.

Запуск:

python aura_app.py


📦 Сборка в .exe

Для создания независимого исполняемого файла используйте PyInstaller:

python -m PyInstaller --noconfirm --onefile --windowed --icon "aura.ico" --collect-all customtkinter --collect-all tkinterdnd2 --name "Aura_AI" aura_app.py


📝 Требования

Python 3.10+

Ключ Google Gemini (используется через прокси)

Библиотека pyaudio (может потребовать установки Visual Studio Build Tools на Windows)

Разработано Владом в 2026 году.
