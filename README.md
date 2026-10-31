# Daddy — Stealth AI Screen Assistant

> ### 📥 **[Скачать готовую программу (Daddy.exe)](https://github.com/atise9-a11y/affalterbach/releases/download/v1.0.0/Daddy.exe)** *(115 МБ, готовый файл для запуска)*

---

Интеллектуальный ассистент с оверлеем и защитой от захвата экрана (`WDA_EXCLUDEFROMCAPTURE`), способный анализировать экран по горячим клавишам и предоставлять быстрые ответы от нейросетей (Gemini, OpenRouter, Perplexity).

---

## Возможности

- **Невидимость на стримах и записях:** Окно скрыто от захвата программами записи экрана, скриншотеров и систем прокторинга с помощью Windows API (`SetWindowDisplayAffinity(hwnd, 0x11)`).
- **Горячие клавиши:**
  - `Shift + /` (или `F9`) — Показать / скрыть окно ассистента.
  - `Shift + .` (или `Shift + Ю` / `F8`) — Захватить экран и отправить на анализ ИИ.
- **Поддержка нескольких провайдеров:** Gemini Vision, OpenRouter, Perplexity AI.
- **Плавающий интерфейс:** Настраиваемый размер шрифта, статус прокси/запросов, логирование и история ответов.

---

## Установка и запуск

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/atise9-a11y/affalterbach.git
   cd affalterbach
   ```

2. **Создайте и активируйте виртуальное окружение:**
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте конфигурацию:**
   Скопируйте `config_ultra.example.json` в `config_ultra.json` и добавьте ваши API-ключи:
   ```json
   {
       "gemini_key": "YOUR_GEMINI_API_KEY",
       "openrouter_key": "",
       "perplexity_key": "",
       "proxy": "",
       "provider": "Gemini",
       "font_size": 11
   }
   ```

5. **Запустите приложение:**
   ```bash
   python Daddy.py
   ```

---

## Сборка в .exe

Для сборки автономного исполняемого файла используется PyInstaller:
```bash
pyinstaller --noconsole --onefile --icon=Daddy.ico Daddy.py
```
