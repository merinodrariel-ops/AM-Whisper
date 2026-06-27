import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import keyboard
import ctypes
import winsound
import time
import os
import subprocess
import tkinter as tk
import traceback

# Configuración de audio
samplerate = 16000
channels = 1
q = queue.Queue()

recording = False
audio_data = []
audio_thread = None
last_toggle_time = 0
toggle_lock = threading.Lock()
key_is_pressed = False
overlay = None

# Rutas locales de Whisper
WHISPER_BIN = r"C:\Users\drari\Documents\Proyectos IA\AM-Whisper\bin\whisper-cli.exe"
MODEL_PATH = os.path.expanduser(r"~\\.cache\whisper\ggml-large-v3-turbo.bin")
LOG_PATH = r"C:\Users\drari\Documents\Proyectos IA\AM-Whisper\dictado.log"

def log_print(msg):
    """Escribe en la consola y en el archivo de log."""
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


class DictationOverlay:
    """HUD flotante semi-transparente similar a la versión de macOS."""
    def __init__(self):
        self.root = None
        self.canvas = None
        self.dot = None
        self.label = None
        self.meter_level = None
        self.thread = None
        self.running = False
        self.blink_state = True
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def _run(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg="black")
        self.root.attributes("-transparentcolor", "black")
        
        w = 260
        h = 44
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = sh - 130
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        self.canvas = tk.Canvas(self.root, width=w, height=h, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        self.canvas.create_rectangle(1, 1, w-1, h-1, fill="#121212", outline="#2c2c2c", width=1)
        self.dot = self.canvas.create_oval(14, 14, 28, 28, fill="#ff3b30", outline="")
        self.label = self.canvas.create_text(38, 22, text="GRABANDO...", fill="#ffffff", font=("Segoe UI", 10, "bold"), anchor="w")
        
        self.canvas.create_rectangle(170, 18, 246, 26, fill="#222222", outline="")
        self.meter_level = self.canvas.create_rectangle(170, 18, 170, 26, fill="#34c759", outline="")
        
        self._blink()
        self.root.mainloop()
        
    def _blink(self):
        if self.running and self.root and self.canvas and self.dot:
            color = "#ff3b30" if self.blink_state else "#331111"
            self.blink_state = not self.blink_state
            self.canvas.itemconfig(self.dot, fill=color)
            self.root.after(500, self._blink)
            
    def update_volume(self, rms):
        if self.running and self.root and self.canvas and self.meter_level:
            val = min(rms / 0.04, 1.0)
            width = val * 76
            self.root.after(0, lambda: self.canvas.coords(self.meter_level, 170, 18, 170 + int(width), 26))
            
    def set_transcribing(self):
        if self.running and self.root:
            self.root.after(0, self._set_transcribing_ui)
            
    def _set_transcribing_ui(self):
        if self.canvas:
            self.running = False
            self.canvas.itemconfig(self.dot, fill="#ffcc00")
            self.canvas.itemconfig(self.label, text="TRANSCRIBIENDO...")
            self.canvas.coords(self.meter_level, 170, 18, 170, 26)
            
    def stop(self):
        self.running = False
        if self.root:
            self.root.after(0, self.root.destroy)
            if self.thread:
                self.thread.join(timeout=0.5)
            self.root = None


def set_clipboard_text(text):
    """Copia texto al portapapeles de Windows de forma nativa usando ctypes en UTF-16."""
    try:
        ctypes.windll.user32.OpenClipboard(0)
        ctypes.windll.user32.EmptyClipboard()
        encoded = text.encode('utf-16-le')
        hcd = ctypes.windll.kernel32.GlobalAlloc(2, len(encoded) + 2)
        ptr = ctypes.windll.kernel32.GlobalLock(hcd)
        ctypes.cdll.msvcrt.memcpy(ptr, encoded, len(encoded))
        ctypes.windll.kernel32.GlobalUnlock(hcd)
        ctypes.windll.user32.SetClipboardData(13, hcd)
        ctypes.windll.user32.CloseClipboard()
        log_print(f"📋 Copiado al portapapeles: '{text}'")
    except Exception as e:
        log_print(f"❌ Error al copiar al portapapeles: {e}")
        log_print(traceback.format_exc())


def callback(indata, frames, time_info, status):
    """Callback de entrada de audio para sounddevice."""
    if status:
        log_print(f"Status micrófono: {status}")
    q.put(indata.copy())
    
    global recording, overlay
    if recording and overlay:
        rms = np.sqrt(np.mean(indata**2))
        overlay.update_volume(rms)


def record_thread():
    """Hilo encargado de capturar el audio del micrófono."""
    global audio_data, recording
    audio_data = []
    while not q.empty():
        q.get()
        
    try:
        with sd.InputStream(samplerate=samplerate, channels=channels, callback=callback):
            while recording:
                try:
                    data = q.get(timeout=0.1)
                    audio_data.append(data)
                except queue.Empty:
                    pass
    except Exception as e:
        log_print(f"❌ Error al abrir el micrófono: {e}")
        log_print(traceback.format_exc())
        recording = False
        winsound.Beep(400, 500)
        global overlay
        if overlay:
            overlay.stop()
            overlay = None


def start_recording():
    """Inicia la grabación y enciende el HUD flotante."""
    global recording, audio_thread, overlay
    recording = True
    
    overlay = DictationOverlay()
    overlay.start()
    
    audio_thread = threading.Thread(target=record_thread)
    audio_thread.start()
    log_print("🎤 Grabación iniciada. Capturando audio...")


def transcribe(wav_path):
    """Llama al binario de Whisper para transcribir y escribe el resultado."""
    log_print("⏳ Iniciando proceso de transcripción...")
    
    cmd = [
        WHISPER_BIN,
        "-m", MODEL_PATH,
        "-f", wav_path,
        "-otxt",
        "-l", "es",
        "-nt"
    ]
    
    try:
        log_print(f"Ejecutando comando: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        log_print(f"Resultado retorno: {res.returncode}")
        if res.returncode != 0:
            log_print(f"STDERR de Whisper: {res.stderr}")
            
        txt_path = wav_path + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            
            try:
                os.remove(wav_path)
                os.remove(txt_path)
                log_print("Limpieza de archivos temporales completada.")
            except Exception as e:
                log_print(f"Error al limpiar temporales: {e}")
                
            if text:
                log_print(f"✨ Texto transcripto con éxito: '{text}'")
                set_clipboard_text(text)
                
                # Simular Ctrl + V
                log_print("Pegando texto en ventana activa (Ctrl+V)...")
                time.sleep(0.15)
                keyboard.press_and_release('ctrl+v')
                
                winsound.Beep(1200, 100)
                time.sleep(0.05)
                winsound.Beep(1200, 100)
            else:
                log_print("⚠️ No se detectó ninguna palabra hablada (archivo vacío).")
                winsound.Beep(500, 300)
        else:
            log_print(f"❌ Error: El archivo txt '{txt_path}' no fue creado por whisper-cli.")
            winsound.Beep(500, 300)
            if os.path.exists(wav_path):
                os.remove(wav_path)
    except Exception as e:
        log_print(f"❌ Error durante la transcripción: {e}")
        log_print(traceback.format_exc())
        winsound.Beep(500, 500)
        if os.path.exists(wav_path):
            os.remove(wav_path)
    finally:
        global overlay
        if overlay:
            overlay.stop()
            overlay = None
        log_print("Proceso de dictado finalizado.")


def stop_recording():
    """Detiene la grabación y cambia el HUD a modo transcribiendo."""
    global recording, overlay
    recording = False
    
    if overlay:
        overlay.set_transcribing()
        
    if audio_thread:
        audio_thread.join()
        
    if audio_data:
        full_audio = np.concatenate(audio_data, axis=0)
        temp_wav = "temp_dictado.wav"
        sf.write(temp_wav, full_audio, samplerate)
        log_print(f"Audio guardado en temporales: '{temp_wav}' (Tamaño: {len(full_audio)} frames)")
        
        threading.Thread(target=transcribe, args=(temp_wav,)).start()
    else:
        log_print("⚠️ Grabación detenida pero no hay datos de audio recopilados.")
        winsound.Beep(500, 300)
        if overlay:
            overlay.stop()
            overlay = None


def toggle_recording(e=None):
    """Manejador de la pulsación de hotkey."""
    global recording, last_toggle_time
    with toggle_lock:
        now = time.time()
        if now - last_toggle_time < 0.5:
            return
        last_toggle_time = now
        
        if not recording:
            winsound.Beep(1000, 150)
            start_recording()
        else:
            winsound.Beep(800, 150)
            stop_recording()


def main():
    # Limpiar log anterior al iniciar
    try:
        if os.path.exists(LOG_PATH):
            os.remove(LOG_PATH)
    except Exception:
        pass

    log_print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log_print("🎙️  AM VOICE DICTATION (Local Whisper Windows)")
    log_print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log_print("Estado: Listo ⚡")
    log_print("Hotkey: Presiona [Control Derecho] (AltGr) para grabar / detener.")
    log_print("Presiona [Ctrl + C] en esta consola para cerrar el dictado.")
    log_print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    global key_is_pressed
    key_is_pressed = False
    
    def handle_key_event(e):
        global key_is_pressed
        is_target_key = (e.scan_code == 541 or e.name == 'alt gr' or e.name == 'right windows')
        if not is_target_key:
            return
            
        if e.event_type == 'down':
            if not key_is_pressed:
                key_is_pressed = True
                toggle_recording()
        elif e.event_type == 'up':
            key_is_pressed = False
            
    keyboard.hook(handle_key_event)
    
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        log_print("\nCerrando dictado. ¡Hasta luego!")

if __name__ == "__main__":
    main()
