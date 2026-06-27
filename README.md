# AM-Whisper

Sistema de dictado por voz y transcripción local, rápido, privado y gratuito, optimizado para **macOS** (Hammerspoon + Metal GPU) y **Windows** (Python + OpenBLAS CPU).

## Características principales

- **100% Local**: No requiere conexión a Internet ni envía tus datos de audio a servidores externos.
- **Precisión Profesional**: Utiliza el modelo de vanguardia **`large-v3-turbo`** (~1.5 GB), optimizado para español de España y Latinoamérica.
- **HUD Visual**: Interfaz flotante con indicador circular de estado (`GRABANDO...` / `TRANSCRIBIENDO...`) y medidor de volumen en tiempo real que reacciona a tu voz.
- **Foco del Teclado**: No roba el foco de tu ventana activa, lo que permite pegar el texto dictado de forma instantánea.
- **Acceso Rápido**: Mapeado a la tecla física a la derecha de la barra espaciadora (`AltGr` en Windows, `Command Derecho` en macOS).

---

## 💻 Versión WINDOWS (Python)

### Requisitos previos
- **Python 3.14** (o versión superior) instalado en la máquina.
- Las librerías necesarias se instalan de forma estándar en Windows (`sounddevice`, `soundfile`, `numpy`, `keyboard`).

### Instalación rápida (Windows)

1. **Clonar este repositorio** en tu carpeta de preferencia.
2. **Descargar el modelo large-v3-turbo** (~1.5 GB) y colocarlo en la caché del sistema:
   * Crea la carpeta `C:\Users\<TuUsuario>\.cache\whisper\` si no existe.
   * Descarga el archivo [ggml-large-v3-turbo.bin](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin) y guárdalo allí.
3. El repositorio ya incluye los binarios de Whisper compilados y optimizados con **OpenBLAS** en la carpeta `bin/`.

### Uso y Funcionamiento (Windows)

1. Haz doble clic en el archivo **`Iniciar-Dictado.bat`**.
   * *Nota: Solicitará permisos de Administrador automáticamente. Esto es obligatorio para poder simular pulsaciones de teclas (`Ctrl + V`) en cualquier aplicación elevada como editores médicos o consolas.*
2. Coloca el cursor en el chat de texto o bloc de notas donde desees escribir.
3. Presiona la tecla **`AltGr`** (la de la derecha del espacio):
   * Sonará un pitido rápido y aparecerá el HUD flotante `🔴 GRABANDO...` en la parte inferior de tu pantalla.
   * Habla con normalidad. La barra verde se moverá según la intensidad de tu voz.
4. Presiona **`AltGr`** de nuevo para terminar:
   * Sonará otro pitido, la barra cambiará a `⏳ TRANSCRIBIENDO...` con un círculo amarillo.
   * La transcripción terminará en 1-2 segundos y el texto se pegará solo en tu cursor.

### Inicio automático en segundo plano
El instalador configura automáticamente un acceso directo en tu carpeta de Inicio de Windows (`Startup`) para iniciar `am-whisper-dictado.py` de forma 100% invisible en segundo plano cada vez que se encienda la computadora.

---

## 🍎 Versión macOS (Hammerspoon)

### Cómo funciona (macOS)
- Presiona **Command derecho** para empezar a grabar (sonará un pitido y se mostrará la barra de audio flotante).
- Habla y vuelve a presionar **Command derecho** para parar. El texto se pegará de inmediato.
- Presiona **Escape** para cancelar una grabación en curso.

### Instalación rápida (Mac)

1. **Instalar Homebrew** (si no lo tienes):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. **Instalar dependencias**:
   ```bash
   brew install sox whisper-cpp && brew install --cask hammerspoon
   ```
3. **Descargar el modelo large-v3-turbo** (~1.5 GB):
   ```bash
   mkdir -p ~/.cache/whisper && cd ~/.cache/whisper && curl -L "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin" -o ggml-large-v3-turbo.bin
   ```
4. **Instalar el script**:
   * Copia o enlaza el archivo `init.lua` de este repositorio en tu carpeta local `~/.hammerspoon/init.lua`.
5. **Activar**:
   * Abre Hammerspoon desde Aplicaciones.
   * Habilita los accesos de Accesibilidad si te los solicita.
   * Haz clic en el icono de Hammerspoon en la barra de menús superior y selecciona **Reload Config**.

---

## 🎬 Transcripción de Videos (Script NodeJS)

Si deseas transcribir un archivo de video completo localmente (`.mp4`, `.mov`, etc.):

1. Abre una terminal.
2. Ejecuta `node video-transcript.mjs <ruta-del-video>`.
3. El resultado se guardará en un archivo `.txt` en el mismo directorio del video original.
