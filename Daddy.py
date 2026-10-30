import tkinter as tk
from tkinter import scrolledtext, ttk
import keyboard
import pyautogui
import threading
import ctypes
import json
import re
import os
import sys
import requests
import base64
import io
import pystray
import time
import math
from datetime import datetime
from PIL import Image, ImageDraw
import win32clipboard

def get_gear_icon(size=64):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg_color = (155, 196, 238, 255)
    border_color = (130, 175, 220, 255)
    margin = size * 0.05
    radius = size * 0.18
    draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=radius, fill=bg_color, outline=border_color, width=max(1, int(size * 0.02)))
    cx, cy = size / 2, size / 2
    outer_r = size * 0.36
    inner_r = size * 0.27
    hole_r = size * 0.12
    teeth_count = 8
    points = []
    angle_step = (2 * math.pi) / teeth_count
    tooth_width_angle = angle_step * 0.28
    tooth_base_angle = angle_step * 0.45
    for i in range(teeth_count):
        center_a = i * angle_step
        a1 = center_a - tooth_base_angle / 2
        a2 = center_a - tooth_width_angle / 2
        a3 = center_a + tooth_width_angle / 2
        a4 = center_a + tooth_base_angle / 2
        points.append((cx + inner_r * math.cos(a1), cy + inner_r * math.sin(a1)))
        points.append((cx + outer_r * math.cos(a2), cy + outer_r * math.sin(a2)))
        points.append((cx + outer_r * math.cos(a3), cy + outer_r * math.sin(a3)))
        points.append((cx + inner_r * math.cos(a4), cy + inner_r * math.sin(a4)))
    gear_color = (255, 255, 255, 255)
    draw.polygon(points, fill=gear_color)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=gear_color)
    draw.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r], fill=bg_color)
    return img

# --- Configuration & Paths ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, 'config_ultra.json')
HOTKEY_CAPTURE = 'shift+.'
HOTKEY_VISIBILITY = 'shift+/'
WINDOW_TITLE = 'System_Buffer_Service'
TIMEOUT_SEC = 45

# Models
DEFAULT_GEMINI_KEY = ''
MODEL_DIRECT_GEMINI = 'gemini-2.5-flash'
MODEL_OPENROUTER = 'google/gemini-2.0-flash-001'
MODEL_PERPLEXITY = 'sonar'

def get_default_config():
    return {
        'gemini_key': DEFAULT_GEMINI_KEY,
        'openrouter_key': '',
        'perplexity_key': '',
        'proxy': '',
        'provider': 'Gemini',
        'font_size': 11
    }

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def load_config():
    base_cfg = get_default_config()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                base_cfg.update(data)
                # If gemini_key was empty or had the old obsolete AIza key, upgrade to default
                if not base_cfg.get('gemini_key') or base_cfg.get('gemini_key', '').startswith('AIzaSyD'):
                    base_cfg['gemini_key'] = DEFAULT_GEMINI_KEY
                # If provider was OpenRouter with no key/blocked, default to Gemini
                if base_cfg.get('provider') == 'OpenRouter' and not base_cfg.get('openrouter_key'):
                    base_cfg['provider'] = 'Gemini'
        except Exception:
            pass
    else:
        save_config(base_cfg)
    return base_cfg

def get_clipboard_text():
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return data or ''
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return ''

class StealthApp:
    def __init__(self, cfg):
        self.cfg = cfg
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry('420x750+100+100')
        self.root.attributes('-topmost', True, '-toolwindow', True)
        self.root.configure(bg='white')
        self.visible = True

        self.header = tk.Frame(self.root, bg='#f0f0f0', height=10, cursor='fleur')
        self.header.pack(fill='x')
        self.header.bind('<B1-Motion>', self.move_window)

        self.nav = tk.Frame(self.root, bg='white')
        self.nav.pack(fill='x', padx=10, pady=5)

        self.prov_var = tk.StringVar(value=self.cfg.get('provider', 'Gemini'))
        self.prov_menu = ttk.Combobox(self.nav, textvariable=self.prov_var, values=['Gemini', 'OpenRouter', 'Perplexity'], width=12, state='readonly')
        self.prov_menu.pack(side='left')
        self.prov_menu.bind('<<ComboboxSelected>>', self.update_cfg)

        tk.Button(self.nav, text='API/Proxy', command=self.open_api_settings, font=('Arial', 8)).pack(side='right', padx=2)
        tk.Button(self.nav, text='Clear', command=self.clear_history, font=('Arial', 8)).pack(side='right', padx=2)

        self.set_f = tk.Frame(self.root, bg='white')
        self.set_f.pack(fill='x', padx=10)

        self.f_size = tk.IntVar(value=self.cfg.get('font_size', 11))
        tk.Spinbox(self.set_f, from_=8, to=24, textvariable=self.f_size, width=3, command=self.update_font).pack(side='left', padx=5)

        self.alpha_scale = ttk.Scale(self.set_f, from_=0.1, to=1.0, orient='horizontal', command=lambda e: self.root.attributes('-alpha', float(self.alpha_scale.get())))
        self.alpha_scale.set(1.0)
        self.alpha_scale.pack(side='left', fill='x', expand=True, padx=5)

        self.st_f = tk.Frame(self.root, bg='#fafafa')
        self.st_f.pack(fill='x', pady=5)

        self.proxy_dot = tk.Canvas(self.st_f, width=12, height=12, bg='#fafafa', highlightthickness=0)
        self.proxy_dot.pack(side='left', padx=10)
        self.dot_id = self.proxy_dot.create_oval(2, 2, 10, 10, fill='gray')

        self.status_lbl = tk.Label(self.st_f, text='Жду Shift + . ...', bg='#fafafa', font=('Segoe UI', 9, 'bold'))
        self.status_lbl.pack(side='left')

        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=('Segoe UI', self.f_size.get()), bg='white', fg='black', bd=0)
        self.text_area.pack(expand=True, fill='both', padx=10, pady=5)
        self.text_area.tag_configure('bold', font=('Segoe UI', self.f_size.get(), 'bold'))
        self.text_area.tag_configure('ans', font=('Segoe UI', self.f_size.get(), 'bold'), foreground='black')

        tk.Label(self.root, text='System Logs:', bg='white', font=('Arial', 7, 'bold'), fg='gray').pack(anchor='w', padx=10)
        self.log_area = tk.Text(self.root, height=10, font=('Consolas', 8), bg='#f9f9f9', bd=0, fg='#444444')
        self.log_area.pack(fill='x', padx=10, pady=5)

        self.apply_stealth()
        self.create_tray()

    def add_log(self, msg):
        now = datetime.now().strftime('%H:%M:%S')
        self.log_area.insert(tk.END, f'[{now}] {msg}\n')
        self.log_area.see(tk.END)

    def set_status(self, text, col='#444444'):
        self.status_lbl.config(text=text, fg=col)

    def update_proxy_status(self, col):
        self.proxy_dot.itemconfig(self.dot_id, fill=col)

    def move_window(self, event):
        self.root.geometry(f'+{self.root.winfo_pointerx() - 200}+{self.root.winfo_pointery() - 5}')

    def update_cfg(self, e=None):
        self.cfg['provider'] = self.prov_var.get()
        self.cfg['font_size'] = self.f_size.get()
        save_config(self.cfg)

    def update_font(self):
        s = self.f_size.get()
        self.text_area.configure(font=('Segoe UI', s))
        self.text_area.tag_configure('bold', font=('Segoe UI', s, 'bold'))
        self.text_area.tag_configure('ans', font=('Segoe UI', s, 'bold'), foreground='black')
        self.update_cfg()

    def toggle_visibility(self):
        if self.visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.attributes('-topmost', True)
        self.visible = not self.visible

    def clear_history(self):
        self.text_area.delete(1.0, tk.END)
        self.log_area.delete(1.0, tk.END)

    def open_api_settings(self):
        if request_api_window(self):
            new_cfg = load_config()
            self.cfg.update(new_cfg)
            self.prov_var.set(self.cfg.get('provider', 'Gemini'))
            self.add_log('✅ Настройки обновлены.')

    def add_history(self, raw, p_name):
        self.text_area.insert(1.0, f'\n--- {p_name} ---\n', 'gray')
        raw_str = str(raw)
        json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_str, re.DOTALL)
        if json_match:
            try:
                items = list(reversed(json.loads(json_match.group(0))))
                for item in items:
                    q = item.get('question', '?')
                    a = item.get('answer', '?')
                    self.text_area.insert(1.0, f'ОТВЕТ: {a}\n\n', 'ans')
                    self.text_area.insert(1.0, f'Q: {q}\n', 'bold')
                return
            except Exception:
                pass
        self.text_area.insert(1.0, raw_str.strip() + '\n')

    def apply_stealth(self):
        self.root.update()
        hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        if hwnd:
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 17)

    def create_tray(self):
        try:
            img = get_gear_icon(64)
        except Exception:
            img = Image.new('RGB', (64, 64), color=(155, 196, 238))
        self.tray = pystray.Icon('StealthAI', img, 'AI Helper', pystray.Menu(
            pystray.MenuItem('Show', self.toggle_visibility),
            pystray.MenuItem('Exit', lambda i, m: os._exit(0))
        ))
        threading.Thread(target=self.tray.run, daemon=True).start()

def request_api_window(parent):
    win = tk.Toplevel(parent.root)
    win.title('Settings')
    win.geometry('400x500')
    win.attributes('-topmost', True, '-toolwindow', True)
    win.configure(bg='white')
    win.geometry(f'+{(win.winfo_screenwidth() - 400)//2}+{(win.winfo_screenheight() - 500)//2}')

    cfg = load_config()
    entries = {}
    fields = (
        ('gemini_key', 'Gemini Key:'),
        ('openrouter_key', 'OpenRouter Key:'),
        ('perplexity_key', 'Perplexity Key:'),
        ('proxy', 'Proxy (127.0.0.1:33140):')
    )

    for key, label in fields:
        tk.Label(win, text=label, bg='white', font=('Arial', 9)).pack(pady=(10, 0))
        e = tk.Entry(win, width=45)
        e.insert(0, cfg.get(key, ''))
        e.pack(pady=2)
        entries[key] = e
        def make_paste(ent):
            return lambda: (ent.delete(0, tk.END), ent.insert(0, get_clipboard_text()))
        tk.Button(win, text='Вставить', command=make_paste(e)).pack()

    def save():
        for k in entries:
            cfg[k] = entries[k].get().strip()
        if save_config(cfg):
            win.destroy()

    tk.Button(win, text='СОХРАНИТЬ', command=save, bg='black', fg='white', width=20).pack(pady=25)
    win.update()
    hwnd = ctypes.windll.user32.FindWindowW(None, 'Settings')
    if hwnd:
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 17)
    win.grab_set()
    parent.root.wait_window(win)
    return True

def run_ai_logic(app):
    provider = app.prov_var.get()
    px_url = app.cfg.get('proxy', '').strip()
    proxies = {'http': px_url, 'https': px_url} if px_url else None
    hd = {
        'User-Agent': 'Mozilla/5.0 Chrome/120.0.0.0',
        'HTTP-Referer': 'https://localhost'
    }
    prompt_main = 'Extract questions and solve. Output ONLY JSON array: [{"question": "...", "answer": "..."}]'

    try:
        app.set_status('📷 Снимок...', 'orange')
        shot = pyautogui.screenshot()
        buf = io.BytesIO()
        shot.save(buf, format='JPEG', quality=95)
        b64_img = base64.b64encode(buf.getvalue()).decode('ascii')

        result = None
        start_time = time.time()

        if provider == 'Gemini':
            app.set_status('🧠 Анализ Gemini...', 'blue')
            gemini_key = app.cfg.get('gemini_key', '').strip() or DEFAULT_GEMINI_KEY

            # Try models with fallback
            models_to_try = [MODEL_DIRECT_GEMINI, 'gemini-flash-latest', 'gemini-2.5-flash-lite']
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt_main},
                                {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                            ]
                        }
                    ]
                }
                try:
                    r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, proxies=proxies, timeout=TIMEOUT_SEC)
                    if r.status_code == 200:
                        res_json = r.json()
                        parts = res_json.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                        if parts:
                            result = parts[0].get('text', '')
                        break
                    elif r.status_code == 404:
                        continue
                    else:
                        app.add_log(f"🛑 Gemini HTTP {r.status_code}: {r.text[:100]}")
                        break
                except Exception as net_err:
                    app.add_log(f"🛑 Сеть Gemini: {net_err}")
                    break

        elif provider == 'OpenRouter':
            app.set_status('🧠 Анализ OpenRouter...', 'blue')
            openrouter_key = app.cfg.get('openrouter_key', '').strip()
            headers = {
                'Authorization': f'Bearer {openrouter_key}',
                **hd
            }
            data = {
                'model': MODEL_OPENROUTER,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt_main},
                            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64_img}'}}
                        ]
                    }
                ]
            }
            r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=data, proxies=proxies, timeout=TIMEOUT_SEC)
            if r.status_code == 200:
                result = r.json()['choices'][0]['message']['content']
            else:
                app.add_log(f'🛑 Ошибка API: {r.status_code}')

        elif provider == 'Perplexity':
            app.set_status('👁️ OCR (Зрение)...', 'blue')
            ocr_text = None
            gemini_key = app.cfg.get('gemini_key', '').strip() or DEFAULT_GEMINI_KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_DIRECT_GEMINI}:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": "Extract questions text from image exactly."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                        ]
                    }
                ]
            }
            try:
                r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, proxies=proxies, timeout=20)
                if r.status_code == 200:
                    ocr_text = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            except Exception:
                pass

            if ocr_text:
                app.set_status('🧠 Решаю (Perplexity)...', 'blue')
                headers = {'Authorization': f"Bearer {app.cfg.get('perplexity_key', '')}", **hd}
                data = {
                    'model': MODEL_PERPLEXITY,
                    'messages': [
                        {'role': 'system', 'content': 'Expert Solver. Answer strictly JSON based on text.'},
                        {'role': 'user', 'content': f"{prompt_main}\n\nTEXT: {ocr_text}"}
                    ]
                }
                r = requests.post('https://api.perplexity.ai/chat/completions', headers=headers, json=data, proxies=proxies, timeout=TIMEOUT_SEC)
                if r.status_code == 200:
                    result = r.json()['choices'][0]['message']['content']
            else:
                app.add_log('❌ Ошибка: Не удалось распознать текст для Perplexity.')

        if result:
            elapsed = time.time() - start_time
            app.update_proxy_status('green' if elapsed < 15 else 'yellow')
            app.add_history(result, provider)
            app.set_status('✅ Готово', 'green')
        else:
            app.update_proxy_status('red')
            app.set_status('🛑 Ошибка', 'red')

    except Exception as e:
        app.update_proxy_status('red')
        app.set_status('🛑 Ошибка', 'red')
        app.add_log(f'Критика: {e}')

if __name__ == '__main__':
    c = load_config()
    app = StealthApp(c)

    last_toggle_time = 0
    last_capture_time = 0

    def on_key_event(event):
        global last_toggle_time, last_capture_time
        if event.event_type != 'down':
            return

        now = time.time()
        shift_pressed = keyboard.is_pressed('shift')

        # Открытие / закрытие программы: Shift + / (или F9)
        if event.name == 'f9' or (shift_pressed and (event.scan_code in (53, 57397) or event.name in ('/', '?'))):
            if now - last_toggle_time > 0.3:
                last_toggle_time = now
                app.root.after(0, app.toggle_visibility)

        # Захват экрана и решение: Shift + . (или F8)
        elif event.name == 'f8' or (shift_pressed and (event.scan_code in (52, 83) or event.name in ('.', '>', 'ю', 'Ю'))):
            if now - last_capture_time > 0.5:
                last_capture_time = now
                threading.Thread(target=run_ai_logic, args=(app,), daemon=True).start()

    keyboard.hook(on_key_event)
    app.root.mainloop()
