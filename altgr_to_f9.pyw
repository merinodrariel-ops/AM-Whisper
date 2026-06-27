import keyboard

# Remapea AltGr (tecla 'alt gr' o scan code 541) y Command Derecho (Right Windows) a F9
keyboard.add_hotkey('alt gr', lambda: keyboard.send('f9'), suppress=True)
keyboard.add_hotkey(541, lambda: keyboard.send('f9'), suppress=True)
keyboard.add_hotkey('right windows', lambda: keyboard.send('f9'), suppress=True)

# Mantener el script corriendo en segundo plano
keyboard.wait()
