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

# Cola de tareas para comunicar hilos secundarios con el hilo principal
task_queue = queue.Queue()

# Rutas locales de Whisper
WHISPER_BIN = r"C:\Users\drari\Documents\Proyectos IA\AM-Whisper\bin\whisper-cli.exe"
MODEL_PATH = os.path.expanduser(r"~\\.cache\whisper\ggml-large-v3-turbo.bin")
LOG_PATH = r"C:\Users\drari\Documents\Proyectos IA\AM-Whisper\dictado.log"

# Referencias globales del hilo principal
root = None
overlay_win = None

def log_print(msg):
    """Escribe en la consola y en el archivo de log."""
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


class OverlayWindow(tk.Toplevel):
    """HUD flotante semi-transparente que corre 100% en el hilo principal."""
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="black")
        self.attributes("-transparentcolor", "black")
        
        w = 260
        h = 44
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = sh - 130
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        # Evitar tomar el foco en Windows (WS_EX_NOACTIVATE)
        self.update_idletasks()
        try:
            hwnd = self.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)
        except Exception as e:
            log_print(f"Error al configurar foco de ventana: {e}")
            
        self.canvas = tk.Canvas(self, width=w, height=h, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        self.canvas.create_rectangle(1, 1, w-1, h-1, fill="#121212", outline="#2c2c2c", width=1)
        self.dot = self.canvas.create_oval(14, 14, 28, 28, fill="#ff3b30", outline="")
        self.label = self.canvas.create_text(38, 22, text="GRABANDO...", fill="#ffffff", font=("Segoe UI", 10, "bold"), anchor="w")
        
        self.canvas.create_rectangle(170, 18, 246, 26, fill="#222222", outline="")
        self.meter_level = self.canvas.create_rectangle(170, 18, 170, 26, fill="#34c759", outline="")
        
        self.blink_state = True
        self.running = True
        self._blink()
        
    def _blink(self):
        if self.running and self.dot:
            color = "#ff3b30" if self.blink_state else "#331111"
            self.blink_state = not self.blink_state
            self.canvas.itemconfig(self.dot, fill=color)
            self.after(500, self._blink)
            
    def update_volume(self, rms):
        if self.running and self.meter_level:
            val = min(rms / 0.04, 1.0)
            width = val * 76
            self.canvas.coords(self.meter_level, 170, 18, 170 + int(width), 26)
            
    def set_transcribing(self):
        self.running = False
        self.canvas.itemconfig(self.dot, fill="#ffcc00")
        self.canvas.itemconfig(self.label, text="TRANSCRIBIENDO...")
        self.canvas.coords(self.meter_level, 170, 18, 170, 26)
        
    def stop(self):
        self.running = False
        self.destroy()


def set_clipboard_text(text):
    """Copia texto al portapapeles de Windows de forma segura usando el root de tkinter del hilo principal."""
    try:
        global root
        if root:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            log_print(f"📋 Copiado al portapapeles: '{text}'")
    except Exception as e:
        log_print(f"❌ Error al copiar al portapapeles: {e}")
        log_print(traceback.format_exc())


def callback(indata, frames, time_info, status):
    """Callback de entrada de audio para sounddevice."""
    if status:
        log_print(f"Status micrófono: {status}")
    q.put(indata.copy())
    
    global recording
    if recording:
        rms = np.sqrt(np.mean(indata**2))
        # Enviar nivel de volumen al hilo principal
        task_queue.put({'action': 'volume', 'rms': rms})


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
        # Indicar al hilo principal que cierre el overlay
        task_queue.put({'action': 'stop_only'})


def start_recording():
    """Inicia la grabación en segundo plano y notifica al hilo principal para mostrar el HUD."""
    global recording, audio_thread
    recording = True
    
    # Notificar al hilo principal para mostrar la interfaz
    task_queue.put({'action': 'start_recording'})
    
    audio_thread = threading.Thread(target=record_thread)
    audio_thread.start()
    log_print("🎤 Grabación iniciada. Capturando audio...")


def transcribe(wav_path):
    """Llama al binario de Whisper para transcribir en segundo plano."""
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
                # Mandar tarea de pegado al hilo principal
                task_queue.put({'action': 'paste_and_stop', 'text': text})
            else:
                log_print("⚠️ No se detectó ninguna palabra hablada (archivo vacío).")
                winsound.Beep(500, 300)
                task_queue.put({'action': 'stop_only'})
        else:
            log_print(f"❌ Error: El archivo txt '{txt_path}' no fue creado por whisper-cli.")
            winsound.Beep(500, 300)
            if os.path.exists(wav_path):
                os.remove(wav_path)
            task_queue.put({'action': 'stop_only'})
    except Exception as e:
        log_print(f"❌ Error durante la transcripción: {e}")
        log_print(traceback.format_exc())
        winsound.Beep(500, 500)
        if os.path.exists(wav_path):
            os.remove(wav_path)
        task_queue.put({'action': 'stop_only'})


def stop_recording():
    """Detiene la grabación y dispara la transcripción en segundo plano."""
    global recording
    recording = False
    
    # Cambiar HUD a modo transcribiendo
    task_queue.put({'action': 'set_transcribing'})
        
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
        task_queue.put({'action': 'stop_only'})


def toggle_recording(e=None):
    """Manejador de la pulsación de hotkey."""
    global recording, last_toggle_time
    with toggle_lock:
        now = time.time()
        diff = now - last_toggle_time
        if diff < 0.8:
            log_print(f"Toggle ignorado por debounce ({diff:.2f}s < 0.8s).")
            return
        last_toggle_time = now
        
        if not recording:
            winsound.Beep(1000, 150)
            start_recording()
        else:
            winsound.Beep(800, 150)
            stop_recording()


def poll_queue():
    """Función periódica en el hilo principal para ejecutar operaciones de interfaz y pegado."""
    global overlay_win, root
    try:
        while True:
            # Leer sin bloquear
            task = task_queue.get_nowait()
            action = task['action']
            
            if action == 'start_recording':
                if not overlay_win:
                    overlay_win = OverlayWindow(root)
            elif action == 'set_transcribing':
                if overlay_win:
                    overlay_win.set_transcribing()
            elif action == 'volume':
                if overlay_win:
                    overlay_win.update_volume(task['rms'])
            elif action == 'paste_and_stop':
                # 1. Cerrar interfaz flotante primero
                if overlay_win:
                    overlay_win.stop()
                    overlay_win = None
                
                # 2. Copiar texto al portapapeles
                text = task['text']
                set_clipboard_text(text)
                
                # 3. Simular pegado
                log_print("Pegando texto en ventana activa (Ctrl+V)...")
                time.sleep(0.2)
                keyboard.press_and_release('ctrl+v')
                
                # Pitidos
                winsound.Beep(1200, 100)
                time.sleep(0.05)
                winsound.Beep(1200, 100)
                log_print("Proceso de dictado finalizado.")
                
            elif action == 'stop_only':
                if overlay_win:
                    overlay_win.stop()
                    overlay_win = None
                log_print("Proceso de dictado cancelado/finalizado con error.")
                
    except queue.Empty:
        pass
    
    # Volver a programar el sondeo de cola en 50ms
    if root:
        root.after(50, poll_queue)


def main():
    global root
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
    
    global last_toggle_time
    last_toggle_time = 0
    
    def handle_key_event(e):
        is_target_key = (e.scan_code == 541 or e.name == 'alt gr' or e.name == 'right windows')
        if not is_target_key:
            return
            
        log_print(f"Tecla detectada: {e.name} | ScanCode: {e.scan_code} | Tipo: {e.event_type}")
        if e.event_type == 'down':
            toggle_recording()
            
    keyboard.hook(handle_key_event)
    
    # Iniciar root oculto de Tkinter en el hilo principal
    root = tk.Tk()
    root.withdraw()
    
    # Programar el lector de la cola en el bucle principal
    root.after(50, poll_queue)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        log_print("\nCerrando dictado. ¡Hasta luego!")

if __name__ == "__main__":
    main()
