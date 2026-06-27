import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import keyboard
import time

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("🔍 CAPTURADOR DE TECLAS (AM-Whisper)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("1. Presiona la tecla a la derecha del espacio 3 veces seguidas.")
print("2. Espera a que esta ventana se cierre sola en 5 segundos.")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

events = []

def on_key(e):
    if e.event_type == 'down':
        events.append(f"Tecla: {e.name} | ScanCode: {e.scan_code}")

keyboard.hook(on_key)
time.sleep(5)
keyboard.unhook_all()

with open("key_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(events))

print("¡Listo! Datos guardados en key_log.txt.")
