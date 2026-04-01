✨ Aura AI Assistant

<p align="center">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Python-3.10%2B-blue%3Fstyle%3Dfor-the-badge%26logo%3Dpython%26logoColor%3Dwhite" alt="Python">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/AI-Gemini_2.5_Flash-orange%3Fstyle%3Dfor-the-badge%26logo%3Dgoogle-gemini%26logoColor%3Dwhite" alt="Gemini">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/UI-CustomTkinter-black%3Fstyle%3Dfor-the-badge" alt="UI">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/OS-Windows-0078D4%3Fstyle%3Dfor-the-badge%26logo%3Dwindows%26logoColor%3Dwhite" alt="Windows">
</p>

Aura AI — это мощный десктопный ассистент с премиальным Amoled Black дизайном, созданный для того, чтобы нейросеть всегда была у вас под рукой. В отличие от обычных чатов, Aura интегрирована прямо в систему и готова к выполнению реальных задач.

🌟 Почему это круто?

👁️ Зрение: Анализируйте происходящее на экране одним кликом или просто перетащите картинку в окно.

🎙️ Голос: Общайтесь голосом. Aura слышит вас и озвучивает свои ответы.

🌐 Живые данные: Переключатель «Поиск в сети» позволяет ИИ выходить в интернет за свежими новостями.

💻 Code Runner: Ассистент не просто пишет код на Python, но и позволяет запустить его прямо внутри приложения.

📂 Умная память: Создавайте разные чаты под разные задачи. Вся история сохраняется автоматически.

👻 Скрытный режим: Сворачивайте приложение в трей и вызывайте его мгновенно через Ctrl + Shift + Space.

📸 Скриншоты

Совет для Влада: Создай в папке проекта папку assets, положи туда скриншот программы с названием preview.png и раскомментируй строку ниже:

<!--  -->

🛠 Инструкция по установке

1. Подготовка окружения

Убедитесь, что у вас установлен Python 3.10 или новее.

2. Клонирование и установка

Откройте терминал (PowerShell) и выполните:

# Клонируем проект
git clone [https://github.com/ВАШ_НИК/AuraAssistant.git](https://github.com/ВАШ_НИК/AuraAssistant.git)
cd AuraAssistant

# Устанавливаем все нужные библиотеки
pip install -r requirements.txt


3. Настройка Proxy

Для работы без блокировок используйте Google Apps Script Proxy. Укажите свой URL в переменной окружения GAS_PROXY_URL или замените значение в начале файла aura_app.py.

4. Запуск

python aura_app.py


📦 Сборка в один .exe файл

Чтобы превратить скрипт в готовую программу с иконкой, выполните команду:

python -m PyInstaller --noconfirm --onefile --windowed --icon "aura.ico" --collect-all customtkinter --collect-all tkinterdnd2 --name "Aura_AI" aura_app.py


📋 Системные требования

ОС: Windows 10/11

Микрофон: Требуется для голосового ввода

Интернет: Стабильное соединение для связи с API

Разработано с любовью Владом в 2026 году. Поставьте ⭐, если проект вам понравился!
