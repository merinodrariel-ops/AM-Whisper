#!/bin/bash

# Navegar a la carpeta del script
cd "$(dirname "$0")"

# Título bonito
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬  AM VIDEO TRANSCRIPT — Dr. Ariel Merino"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 INSTRUCCIONES:"
echo "1. Arrastrá el archivo de video a esta ventana."
echo "2. Presioná la tecla ENTER."
echo ""
echo "👇 Arrastrá el video aquí:"

# Leer la ruta del archivo
read inputPath

# Limpiar la ruta (quitar espacios extras o comillas que pone macOS al arrastrar)
# También manejamos el caso de que el path venga con escape characters
videoPath=$(echo "$inputPath" | sed "s/^'//;s/'$//;s/\\\\//g")

if [ -z "$videoPath" ]; then
    echo "❌ No se ingresó ningún archivo."
    sleep 2
    exit 1
fi

echo ""
echo "🚀 Iniciando transcripción..."
echo "------------------------------------------------------------"

# Ejecutar el script de Node
node video-transcript.mjs "$videoPath"

echo "------------------------------------------------------------"
echo "🏁 Proceso finalizado."
echo "Presioná cualquier tecla para salir..."
read -n 1 -s
exit 0
