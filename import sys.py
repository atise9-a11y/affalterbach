import sys
import threading
import base64
import requests
import keyboard
from mss import mss
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
import ctypes

# --- НАСТРОЙКИ ---
API_KEY = "YOUR_OPENROUTER_API_KEY" # Замени на свой ключ
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-001" # Или другая модель с поддержкой зрения

class AiAssistantWindow(QMainWindow):
    update_text_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.update_text_signal.connect(self.update_display)
        
        # Скрываем окно при запуске
        self.hide()

    def init_ui(self):
        # Флаги: всегда сверху, окно-инструмент (нет в панели задач)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Защита от захвата экрана (черный экран для систем слежки)
        hwnd = self.winId().__int__()
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)

        # Контейнер и поле текста
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            background-color: rgba(30, 30, 30, 220);
            color: #00FF00;
            font-size: 14px;
            border: 1px solid #555;
            border-radius: 10px;
        """)
        layout.addWidget(self.text_display)
        
        self.setGeometry(100, 100, 400, 250)

    @pyqtSlot(str)
    def update_display(self, text):
        self.text_display.append(f"<b>AI:</b> {text}<br>---")
        if not self.isVisible():
            self.show()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

def capture_and_process(window):
    window.update_text_signal.emit("Анализирую экран...")
    
    try:
        with mss() as sct:
            # Захват экрана
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img_bytes = requests.utils.dict_from_cookiejar(requests.cookies.RequestsCookieJar()) # заглушка
            
            # Сохранение во временный буфер и кодирование в base64
            import io
            from PIL import Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70) # Сжимаем для скорости
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Запрос к ИИ
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Что на экране? Дай краткий и четкий ответ."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }

        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        result = response.json()
        
        if "choices" in result:
            answer = result["choices"][0]["message"]["content"]
            window.update_text_signal.emit(answer)
        else:
            window.update_text_signal.emit(f"Ошибка API: {result}")

    except Exception as e:
        window.update_text_signal.emit(f"Ошибка: {str(e)}")

def run_app():
    app = QApplication(sys.argv)
    win = AiAssistantWindow()

    # Горячие клавиши
    # F9 — показать/скрыть окно
    keyboard.add_hotkey('f9', win.toggle_visibility)
    
    # F8 — сделать скриншот и отправить в ИИ
    keyboard.add_hotkey('f8', lambda: threading.Thread(target=capture_and_process, args=(win,), daemon=True).start())

    print("Приложение запущено. F9 — окно, F8 — анализ.")
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()