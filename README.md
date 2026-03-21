# AM-Whisper

Sistema de transcripción de voz local usando whisper.cpp + Hammerspoon para Mac.
Gratis, sin internet, sin suscripción. Transcripción casi instantánea con aceleración Metal en Apple Silicon.

## Cómo funciona

- Presioná **Command derecho** para empezar a grabar
- Hablá lo que quieras
- Presioná **Command derecho** de nuevo para parar y transcribir
- El texto se pega automáticamente donde tenés el cursor
- Mientras grabás aparece un medidor de audio en la parte inferior de la pantalla

## Características

- **Velocidad**: whisper.cpp con Metal GPU — transcripción en ~1-2 segundos
- **Precisión**: modelo large-v3-turbo, optimizado para español
- **Prompts contextuales**: detecta la app activa y ajusta el vocabulario automáticamente
  - **Antigravity** (consultorio): términos médicos
  - **Cursor / VS Code**: terminología de desarrollo
  - **Claude**: contexto de IA
- **Medidor de audio**: barra visual en tiempo real mientras grabás

## Instalación en Mac nueva

### 1. Instalar Homebrew (si no lo tenés)

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Luego agregar al PATH:

    echo >> ~/.zprofile && echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> ~/.zprofile && eval "$(/opt/homebrew/bin/brew shellenv zsh)"

### 2. Instalar dependencias

    brew install sox whisper-cpp && brew install --cask hammerspoon

### 3. Bajar el modelo large-v3-turbo (~1.5 GB)

    mkdir -p ~/.cache/whisper && cd ~/.cache/whisper && curl -L "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin" -o ggml-large-v3-turbo.bin

### 4. Bajar el script y enlazarlo

    mkdir -p ~/.hammerspoon
    curl -o ~/.hammerspoon/init.lua https://raw.githubusercontent.com/merinodrariel-ops/AM-Whisper/main/init.lua

### 5. Activar

1. Abrí Hammerspoon desde Aplicaciones
2. Habilitá Accesibilidad cuando te lo pida
3. Clic en el ícono de Hammerspoon → Reload Config
4. Listo — aparece "Whisper listo ⚡ Command derecho para grabar"

## Notas

- Todo corre local, nada sale a internet
- Compatible con Mac Apple Silicon (M1/M2/M3/M4) — usa Metal para máxima velocidad
- Para agregar prompts contextuales de otras apps, editá el array `contextPrompts` en `init.lua`
