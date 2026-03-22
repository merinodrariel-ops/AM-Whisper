local recording = false
local recordingTask = nil
local tap = nil
local focusedWindow = nil
local meterCanvas = nil
local levelTimer = nil
local whisperWatchdog = nil

local home = os.getenv("HOME")
local whisperBin = "/opt/homebrew/bin/whisper-cli"
local modelPath = home .. "/.cache/whisper/ggml-large-v3-turbo.bin"

-- Prompts contextuales según la app enfocada
local contextPrompts = {
    ["Antigravity"] = "Consulta médica de consultorio clínico. Términos frecuentes: paciente, diagnóstico, tratamiento, síntoma, medicamento, dosis, derivación, evolución, antecedente, obra social, turno, guardia, internación, cirugía, ecografía, laboratorio, presión arterial, glucemia.",
    ["Claude"]  = "Conversación con asistente de inteligencia artificial sobre desarrollo de software y producto.",
    ["Cursor"]  = "Desarrollo de software. Términos: función, componente, variable, API, base de datos, bug, refactor, commit, branch.",
    ["Code"]    = "Desarrollo de software. Términos: función, componente, variable, API, base de datos, bug, refactor.",
    ["Chrome"]  = nil,
    ["Safari"]  = nil,
}

local function getPromptForApp()
    local app = hs.application.frontmostApplication()
    if not app then return nil end
    local name = app:name()
    for appName, prompt in pairs(contextPrompts) do
        if name:find(appName) then return prompt end
    end
    return nil
end

-- ── Medidor de audio ──────────────────────────────────────────────────────────

local METER_W = 200
local METER_H = 44
local BAR_X   = 42
local BAR_MAX  = 200 - 42 - 12  -- 146px de barra util

local function showMeter()
    if meterCanvas then meterCanvas:delete() end
    local screen = hs.screen.mainScreen()
    local sf = screen:frame()
    -- Centrado horizontalmente, 28% desde arriba (donde va el alert de HS)
    local cx = sf.x + (sf.w - METER_W) / 2
    local cy = sf.y + sf.h - 110
    meterCanvas = hs.canvas.new({x = cx, y = cy, w = METER_W, h = METER_H})
    -- Fondo oscuro redondeado
    meterCanvas[1] = {
        type = "rectangle",
        fillColor = {red = 0.1, green = 0.1, blue = 0.1, alpha = 0.92},
        roundedRectRadii = {xRadius = 14, yRadius = 14},
        frame = {x = 0, y = 0, w = METER_W, h = METER_H}
    }
    -- Carril de la barra (track oscuro)
    meterCanvas[2] = {
        type = "rectangle",
        fillColor = {red = 0.05, green = 0.05, blue = 0.05, alpha = 0.9},
        roundedRectRadii = {xRadius = 6, yRadius = 6},
        frame = {x = BAR_X, y = 18, w = BAR_MAX, h = METER_H - 36}
    }
    -- Barra de nivel activa (empieza en 0)
    meterCanvas[3] = {
        type = "rectangle",
        fillColor = {red = 0.2, green = 0.85, blue = 0.3, alpha = 0.95},
        roundedRectRadii = {xRadius = 6, yRadius = 6},
        frame = {x = BAR_X, y = 18, w = 0, h = METER_H - 36}
    }
    -- Ícono 🔴
    meterCanvas[4] = {
        type = "text",
        text = "🔴",
        textSize = 20,
        frame = {x = 12, y = 13, w = 30, h = 30}
    }
    meterCanvas:level(1000)
    meterCanvas:show()
end

local function updateMeter(rms)
    if not meterCanvas then return end
    -- Voz normal: 0.003-0.04 RMS. Normalizamos con techo en 0.020
    local normalized = math.min(rms / 0.020, 1.0)
    local barW = math.max(BAR_MAX * normalized, 3)
    local r = math.min(normalized * 2.0, 1.0)
    local g = math.max(1.0 - normalized * 1.3, 0.1)
    meterCanvas[3] = {
        type = "rectangle",
        fillColor = {red = r, green = g, blue = 0.05, alpha = 0.95},
        roundedRectRadii = {xRadius = 6, yRadius = 6},
        frame = {x = BAR_X, y = 18, w = barW, h = METER_H - 36}
    }
end

local function startLevelSampling()
    if levelTimer then levelTimer:stop() end
    levelTimer = hs.timer.doEvery(0.18, function()
        -- Muestra 80ms de audio y calcula el RMS — corre en paralelo al sox principal
        hs.task.new("/opt/homebrew/bin/sox",
            function(code, stdout, stderr)
                if stderr then
                    local rms = tonumber(stderr:match("RMS%s+amplitude:%s+([%d%.]+)"))
                    if rms then updateMeter(rms) end
                end
            end,
            {"-d", "-n", "trim", "0.0", "0.08", "stat"}
        ):start()
    end)
end

local function hideMeter()
    if levelTimer then levelTimer:stop(); levelTimer = nil end
    if meterCanvas then
        meterCanvas:delete()
        meterCanvas = nil
    end
end

-- ── Tap principal ─────────────────────────────────────────────────────────────

local function startTap()
    if tap then tap:stop() end
    tap = hs.eventtap.new({hs.eventtap.event.types.flagsChanged}, function(event)
        local keyCode = event:getKeyCode()
        -- Command derecho (key code 54)
        if keyCode ~= 54 then return false end
        local flags = event:getFlags()

        if not flags.cmd then
            if not recording then
                -- ── INICIO DE GRABACIÓN ──────────────────────────────────────
                focusedWindow = hs.window.focusedWindow()
                recording = true
                os.remove("/tmp/voice_input.wav")
                os.remove("/tmp/voice_input.txt")
                showMeter()
                startLevelSampling()

                recordingTask = hs.task.new("/opt/homebrew/bin/sox", nil,
                    {"-d", "/tmp/voice_input.wav"})
                recordingTask:start()

            else
                -- ── FIN DE GRABACIÓN Y TRANSCRIPCIÓN ────────────────────────
                recording = false
                hs.alert.closeAll()
                hideMeter()
                -- Detenemos el tap mientras transcribe para evitar solapamientos
                if tap then tap:stop() end
                hs.alert.show("⏳ Transcribiendo...", 30)

                local function startTranscription()
                    local onComplete = function(code, stdout, stderr)
                        if whisperWatchdog then whisperWatchdog:stop(); whisperWatchdog = nil end
                        hs.alert.closeAll()

                        if code ~= 0 then
                            hs.alert.show("❌ Error Whisper: " .. (stderr or "desconocido"), 5)
                            print("Whisper error: " .. (stderr or ""))
                            hs.timer.doAfter(0.3, startTap)
                            return
                        end

                        local f = io.open("/tmp/voice_input.txt")
                        if f then
                            local text = f:read("*a")
                            f:close()
                            text = text:gsub("^%s*(.-)%s*$", "%1")
                            if text ~= "" then
                                hs.pasteboard.setContents(text)
                                if focusedWindow then focusedWindow:focus() end
                                hs.timer.doAfter(0.2, function()
                                    hs.eventtap.keyStroke({"cmd"}, "v")
                                    local preview = text:len() > 60 and text:sub(1, 60) .. "…" or text
                                    hs.alert.show("✅ " .. preview, 3)
                                end)
                            else
                                hs.alert.show("⚠️ No se detectó texto", 2)
                            end
                        else
                            hs.alert.show("❌ Error: no se encontró el archivo de salida", 3)
                        end

                        os.remove("/tmp/voice_input.wav")
                        os.remove("/tmp/voice_input.txt")
                        hs.timer.doAfter(0.3, startTap)
                    end

                    local onStream = function(task, stdout, stderr)
                        if stdout and stdout ~= "" then print("whisper: " .. stdout) end
                        if stderr and stderr ~= "" then print("whisper: " .. stderr) end
                        return true
                    end

                    -- Construir argumentos para whisper-cli
                    local prompt = getPromptForApp()
                    local whisperArgs = {
                        "-m", modelPath,
                        "-f", "/tmp/voice_input.wav",
                        "--output-txt",
                        "-of", "/tmp/voice_input",
                        "-l", "es",
                    }
                    if prompt then
                        table.insert(whisperArgs, "--prompt")
                        table.insert(whisperArgs, prompt)
                    end

                    local whisperTask = hs.task.new(whisperBin, onComplete, onStream, whisperArgs)
                    whisperTask:start()

                    -- Watchdog: si whisper se cuelga y onComplete nunca llega, el tap queda muerto.
                    -- A los 120s forzamos el restart para que el usuario pueda volver a grabar.
                    if whisperWatchdog then whisperWatchdog:stop() end
                    whisperWatchdog = hs.timer.doAfter(120, function()
                        whisperWatchdog = nil
                        whisperTask:terminate()
                        hs.alert.closeAll()
                        hs.alert.show("⚠️ Whisper tardó demasiado, reiniciando…", 3)
                        hs.timer.doAfter(0.3, startTap)
                    end)
                end

                if recordingTask then
                    -- SIGINT permite que sox finalice el header WAV correctamente
                    -- SIGTERM lo mata sin actualizar el tamaño del archivo → whisper trunca
                    local pid = recordingTask:pid()
                    recordingTask = nil
                    hs.task.new("/bin/kill", function()
                        hs.timer.doAfter(0.5, startTranscription)
                    end, {"-INT", tostring(pid)}):start()
                else
                    startTranscription()
                end
            end
        end

        return false
    end)
    tap:start()
end

startTap()
hs.alert.show("Whisper listo ⚡ Command derecho para grabar", 3)
