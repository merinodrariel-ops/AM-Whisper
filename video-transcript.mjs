import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isWin = os.platform() === 'win32';
const WHISPER_BIN = isWin
    ? path.join(__dirname, 'bin', 'whisper-cli.exe')
    : '/opt/homebrew/opt/whisper-cpp/bin/whisper-cli';

const MODEL_PATH = path.join(os.homedir(), '.cache', 'whisper', 'ggml-large-v3-turbo.bin');

async function main() {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log('\n🚀 AM Video Transcript ⚡');
        console.log('Uso: node video-transcript.mjs <ruta-del-video>\n');
        console.log('💡 Tip: Podés arrastrar el video directamente a la terminal.\n');
        process.exit(1);
    }

    const videoPath = args[0].replace(/^& /, '').replace(/'/g, '').trim(); // Limpiar path de Mac (arrastrar y soltar)
    
    if (!fs.existsSync(videoPath)) {
        console.error(`❌ Error: El archivo no existe en la ruta: ${videoPath}`);
        process.exit(1);
    }

    const videoDir = path.dirname(videoPath);
    const videoName = path.basename(videoPath, path.extname(videoPath));
    const tempAudioPath = path.join(videoDir, `${videoName}_temp_audio.wav`);
    const finalMdPath = path.join(videoDir, `${videoName}.md`);

    console.log(`\n🎬 Procesando: ${videoName}`);
    
    try {
        // 1. Extraer audio con ffmpeg (16kHz mono como requiere Whisper)
        console.log('🎵 Extrayendo audio...');
        execSync(`ffmpeg -i "${videoPath}" -ar 16000 -ac 1 -c:a pcm_s16le "${tempAudioPath}" -y`, { stdio: 'ignore' });

        // 2. Transcribir
        console.log(isWin ? '📝 Transcribiendo (usando CPU optimizada OpenBLAS)...' : '📝 Transcribiendo (usando GPU Metal)...');
        // whisper-cli genera el txt automáticamente si pasamos -otxt
        execSync(`"${WHISPER_BIN}" -m "${MODEL_PATH}" -f "${tempAudioPath}" -otxt -l es`, { stdio: 'inherit' });

        // whisper-cli guarda como <wav_path>.txt
        const generatedTxt = `${tempAudioPath}.txt`;
        if (fs.existsSync(generatedTxt)) {
            const rawTranscript = fs.readFileSync(generatedTxt, 'utf8');
            const mdContent = `# Transcripción: ${videoName}\n\n${rawTranscript}`;
            fs.writeFileSync(finalMdPath, mdContent);
            console.log(`\n✅ ¡Listo! Transcripción guardada en:\n📄 ${finalMdPath}\n`);
            
            // Eliminar el txt temporal generado por whisper-cli
            fs.unlinkSync(generatedTxt);
        } else {
            console.error('\n❌ Error: No se pudo generar el archivo de transcripción.');
        }

    } catch (error) {
        console.error('\n❌ Error durante el proceso:', error.message);
    } finally {
        // Limpiar audio temporal
        if (fs.existsSync(tempAudioPath)) {
            fs.unlinkSync(tempAudioPath);
        }
    }
}

main();
