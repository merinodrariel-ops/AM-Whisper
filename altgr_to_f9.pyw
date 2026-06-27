import keyboard

# Remapea AltGr (Right Alt) y Command Derecho (Right Windows) a F9 de forma silenciosa
# suppress=True evita que la tecla original llegue al sistema
keyboard.add_hotkey('right alt', lambda: keyboard.send('f9'), suppress=True)
keyboard.add_hotkey('right windows', lambda: keyboard.send('f9'), suppress=True)

# Mantener el script corriendo en segundo plano
keyboard.wait()
