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

# Configuración de audio
samplerate = 16000
channels = 1
q = queue.Queue()

recording = False
audio_data = []
audio_thread = None
last_toggle_time = 0
toggle_lock = threading.Lock()

# Rutas locales de Whisper
WHISPER_BIN = r"C:\Users\drari\Documents\Proyectos IA\AM-Whisper\bin\whisper-cli.exe"
MODEL_PATH = os.path.expanduser(r"~\\.cache\whisper\ggml-large-v3-turbo.bin")

def set_clipboard_text(text):
    """Copia texto al portapapeles de Windows de forma nativa usando ctypes en UTF-16."""
    try:
        # Abrir portapapeles
        ctypes.windll.user32.OpenClipboard(0)
        ctypes.windll.user32.EmptyClipboard()
        # Codificar en UTF-16 Le
        encoded = text.encode('utf-16-le')
        # Reservar memoria global
        hcd = ctypes.windll.kernel32.GlobalAlloc(2, len(encoded) + 2)
        ptr = ctypes.windll.kernel32.GlobalLock(hcd)
        ctypes.cdll.msvcrt.memcpy(ptr, encoded, len(encoded))
        ctypes.windll.kernel32.GlobalUnlock(hcd)
        # 13 es CF_UNICODETEXT
        ctypes.windll.user32.SetClipboardData(13, hcd)
        ctypes.windll.user32.CloseClipboard()
    except Exception as e:
        print(f"Error al copiar al portapapeles: {e}")

def callback(indata, frames, time_info, status):
    """Callback de entrada de audio para sounddevice."""
    if status:
        print(status, flush=True)
    q.put(indata.copy())

def record_thread():
    """Hilo encargado de capturar el audio del micrófono."""
    global audio_data, recording
    audio_data = []
    # Vaciar la cola por si acaso
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
        print(f"\n❌ Error al abrir el micrófono: {e}")
        recording = False
        winsound.Beep(400, 500)

def start_recording():
    """Inicia la grabación en un hilo separado."""
    global recording, audio_thread
    recording = True
    audio_thread = threading.Thread(target=record_thread)
    audio_thread.start()
    print("\n🎤 Grabando... Habla ahora. Presiona [Control Derecho] para terminar.", flush=True)

def transcribe(wav_path):
    """Llama al binario de Whisper para transcribir y escribe el resultado."""
    print("⏳ Transcribiendo...", flush=True)
    
    # Configuración de argumentos de whisper-cli
    cmd = [
        WHISPER_BIN,
        "-m", MODEL_PATH,
        "-f", wav_path,
        "-otxt",
        "-l", "es",
        "-nt" # Deshabilitar timestamps
    ]
    
    try:
        # Ejecutar de forma silenciosa
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        txt_path = wav_path + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            
            # Limpiar archivos temporales
            try:
                os.remove(wav_path)
                os.remove(txt_path)
            except Exception:
                pass
                
            if text:
                print(f"✨ Transcrito: {text}", flush=True)
                # Copiar al portapapeles
                set_clipboard_text(text)
                
                # Simular Ctrl + V para pegar en la ventana activa
                time.sleep(0.1)
                keyboard.press_and_release('ctrl+v')
                
                # Doble beep rápido indicando éxito
                winsound.Beep(1200, 100)
                time.sleep(0.05)
                winsound.Beep(1200, 100)
            else:
                print("⚠️ No se detectó ninguna palabra hablada.", flush=True)
                winsound.Beep(500, 300)
        else:
            print("❌ Error: No se generó el archivo de texto transcrito.", flush=True)
            winsound.Beep(500, 300)
            if os.path.exists(wav_path):
                os.remove(wav_path)
    except Exception as e:
        print(f"❌ Error al ejecutar Whisper: {e}", flush=True)
        winsound.Beep(500, 500)
        if os.path.exists(wav_path):
            os.remove(wav_path)

def stop_recording():
    """Detiene la grabación y dispara la transcripción."""
    global recording
    recording = False
    if audio_thread:
        audio_thread.join()
        
    if audio_data:
        full_audio = np.concatenate(audio_data, axis=0)
        temp_wav = "temp_dictado.wav"
        sf.write(temp_wav, full_audio, samplerate)
        
        # Ejecutar transcripción en un hilo para no bloquear el listener de teclado
        threading.Thread(target=transcribe, args=(temp_wav,)).start()
    else:
        print("⚠️ No se grabó ningún audio.", flush=True)
        winsound.Beep(500, 300)

def toggle_recording(e=None):
    """Manejador de la pulsación de hotkey."""
    global recording, last_toggle_time
    with toggle_lock:
        now = time.time()
        # Evitar doble disparo por rebote de tecla (500ms)
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
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎙️  AM VOICE DICTATION (Local Whisper Windows)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Estado: Listo ⚡")
    print("Hotkey: Presiona [Control Derecho] (Right Ctrl) para grabar / detener.")
    print("Presiona [Ctrl + C] en esta consola para cerrar el dictado.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # Registrar tecla global (AltGr y Windows Derecho)
    keyboard.on_press_key("alt gr", toggle_recording)
    keyboard.on_press_key("right windows", toggle_recording)
    
    # Mantener el script corriendo
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nCerrando dictado. ¡Hasta luego!")

if __name__ == "__main__":
    main()
