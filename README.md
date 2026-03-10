# AM-Whisper

Sistema de transcripción de voz local usando Whisper + Hammerspoon para Mac.
Gratis, sin internet, sin suscripción.

## Cómo funciona

- Presioná **Command derecho** para empezar a grabar
- Hablá lo que quieras
- Presioná **Command derecho** de nuevo para parar y transcribir
- El texto se pega automáticamente donde tenés el cursor

## Instalación en Mac nueva

### 1. Instalar Homebrew (si no lo tenés)

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Luego agregar al PATH:

    echo >> ~/.zprofile && echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> ~/.zprofile && eval "$(/opt/homebrew/bin/brew shellenv zsh)"

### 2. Instalar dependencias

    brew install ffmpeg sox && brew install --cask hammerspoon && pip3 install openai-whisper

### 3. Agregar Whisper al PATH

    PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") && echo "export PATH=$HOME/Library/Python/$PYVER/bin:$PATH" >> ~/.zprofile && source ~/.zprofile

### 4. Bajar el script

    curl -o ~/.hammerspoon/init.lua https://raw.githubusercontent.com/merinodrariel-ops/AM-Whisper/main/init.lua

### 5. Activar

1. Abrí Hammerspoon desde Aplicaciones
2. Habilitá Accesibilidad cuando te lo pida
3. En la consola de Hammerspoon escribí: hs.reload()
4. Listo!

## Notas

- Modelo: tiny (rápido, preciso en español)
- Todo corre local, nada sale a internet
- Compatible con cualquier Mac (Intel o Apple Silicon)
