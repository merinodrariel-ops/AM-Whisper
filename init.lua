local recording = false
local transcribing = false
local pendingTranscription = false
local cancelRequested = false
local recordingTask = nil
local whisperTask = nil
local tap = nil
local cancelHotkey = nil
local cancelTap = nil
local focusedWindow = nil
local meterCanvas = nil
local statusCanvas = nil
local levelTimer = nil
local whisperWatchdog = nil
local statusTimer = nil

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

local function hideStatus()
    if statusTimer then statusTimer:stop(); statusTimer = nil end
    if statusCanvas then
        statusCanvas:delete()
        statusCanvas = nil
    end
end

local function showStatus(text, fillColor, duration)
    hideStatus()

    local screen = hs.screen.mainScreen()
    local sf = screen:frame()
    local width = 280
    local height = 40
    local cx = sf.x + (sf.w - width) / 2
    local cy = sf.y + sf.h - 165

    statusCanvas = hs.canvas.new({x = cx, y = cy, w = width, h = height})
    statusCanvas[1] = {
        type = "rectangle",
        fillColor = fillColor,
        roundedRectRadii = {xRadius = 12, yRadius = 12},
        frame = {x = 0, y = 0, w = width, h = height}
    }
    statusCanvas[2] = {
        type = "text",
        text = text,
        textSize = 16,
        textColor = {white = 1, alpha = 1},
        frame = {x = 14, y = 9, w = width - 28, h = 22}
    }
    statusCanvas:level(1001)
    statusCanvas:show()

    if duration and duration > 0 then
        statusTimer = hs.timer.doAfter(duration, hideStatus)
    end
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

local startTap  -- declaración anticipada (se define más abajo)

local function cleanupTempFiles()
    os.remove("/tmp/voice_input.wav")
    os.remove("/tmp/voice_input.txt")
end

local function setCancelHotkeyEnabled(enabled)
    if not cancelHotkey then return end
    if enabled then
        cancelHotkey:enable()
    else
        cancelHotkey:disable()
    end
end

local function finishInteraction()
    recording = false
    transcribing = false
    pendingTranscription = false
    cancelRequested = false
    recordingTask = nil
    whisperTask = nil
    hideMeter()
    hideStatus()
    setCancelHotkeyEnabled(false)
    if whisperWatchdog then whisperWatchdog:stop(); whisperWatchdog = nil end
    cleanupTempFiles()
    -- Reiniciar el tap para garantizar estado limpio
    hs.timer.doAfter(0.1, startTap)
end

local function requestRecorderStop()
    if not recordingTask then return end
    local pid = recordingTask:pid()
    if not pid then return end
    hs.task.new("/bin/kill", nil, {"-INT", tostring(pid)}):start()
end

local startTranscription

local function cancelCurrentAction()
    if not recording and not transcribing then return end

    print("AM-Whisper: cancel requested")

    cancelRequested = true
    recording = false
    pendingTranscription = false
    hs.alert.closeAll()
    hideMeter()

    if whisperWatchdog then whisperWatchdog:stop(); whisperWatchdog = nil end

    if whisperTask then
        whisperTask:terminate()
        showStatus("Cancelando transcripcion...", {red = 0.55, green = 0.18, blue = 0.14, alpha = 0.96}, 2)
        return
    end

    if recordingTask then
        requestRecorderStop()
        showStatus("Cancelando grabacion...", {red = 0.55, green = 0.18, blue = 0.14, alpha = 0.96}, 2)
        return
    end

    finishInteraction()
    showStatus("Cancelado", {red = 0.55, green = 0.18, blue = 0.14, alpha = 0.96}, 1.5)
end

-- ── Tap principal ─────────────────────────────────────────────────────────────

startTap = function()
    if tap then tap:stop() end
    tap = hs.eventtap.new({hs.eventtap.event.types.flagsChanged}, function(event)
        local keyCode = event:getKeyCode()
        -- Command derecho (key code 54)
        if keyCode ~= 54 then return false end
        local flags = event:getFlags()

        if not flags.cmd then
            if transcribing then
                -- Si no hay ninguna tarea activa, el estado quedó colgado — recuperar
                if not whisperTask and not recordingTask then
                    print("AM-Whisper: estado colgado detectado, recuperando...")
                    finishInteraction()
                    -- Continúa para iniciar nueva grabación (cae en el elseif de abajo)
                else
                    return false
                end
            end
            if not recording then
                -- ── INICIO DE GRABACIÓN ──────────────────────────────────────
                focusedWindow = hs.window.focusedWindow()
                recording = true
                transcribing = false
                pendingTranscription = false
                cancelRequested = false
                cleanupTempFiles()
                showMeter()
                setCancelHotkeyEnabled(true)
                startLevelSampling()

                recordingTask = hs.task.new("/opt/homebrew/bin/sox", function(code, stdout, stderr)
                    local shouldTranscribe = pendingTranscription and not cancelRequested
                    recordingTask = nil

                    if shouldTranscribe then
                        startTranscription()
                        return
                    end

                    if cancelRequested then
                        hs.alert.closeAll()
                        finishInteraction()
                        showStatus("Cancelado", {red = 0.55, green = 0.18, blue = 0.14, alpha = 0.96}, 1.5)
                        return
                    end

                    if code ~= 0 then
                        hs.alert.closeAll()
                        finishInteraction()
                        hs.alert.show("❌ Error grabando audio", 3)
                        print("Recording error: " .. (stderr or ""))
                    end
                end,
                    {"-d", "/tmp/voice_input.wav"})
                recordingTask:start()

            else
                -- ── FIN DE GRABACIÓN Y TRANSCRIPCIÓN ────────────────────────
                recording = false
                transcribing = true
                pendingTranscription = true
                hs.alert.closeAll()
                hideMeter()
                showStatus("Transcribiendo...", {red = 0.18, green = 0.36, blue = 0.72, alpha = 0.96})

                if recordingTask then
                    -- SIGINT permite que sox cierre el WAV correctamente.
                    -- Esperamos al callback del proceso en vez de usar un delay fijo.
                    requestRecorderStop()
                else
                    startTranscription()
                end
            end
        end

        return false
    end)
    tap:start()
end

cancelHotkey = hs.hotkey.new({}, "escape", function()
    cancelCurrentAction()
end)
setCancelHotkeyEnabled(false)

cancelTap = hs.eventtap.new({hs.eventtap.event.types.keyDown, hs.eventtap.event.types.keyUp}, function(event)
    if not recording and not transcribing then return false end

    local keyCode = event:getKeyCode()
    local eventType = event:getType()
    print("AM-Whisper: key event type=" .. tostring(eventType) .. " keyCode=" .. tostring(keyCode))

    if keyCode ~= 53 then return false end

    print("AM-Whisper: escape detected")
    cancelCurrentAction()
    return true
end)
cancelTap:start()

startTranscription = function()
    if cancelRequested then
        hs.alert.closeAll()
        finishInteraction()
        showStatus("Cancelado", {red = 0.55, green = 0.18, blue = 0.14, alpha = 0.96}, 1.5)
        return
    end

    local onComplete = function(code, stdout, stderr)
        local wasCancelled = cancelRequested

        if whisperWatchdog then whisperWatchdog:stop(); whisperWatchdog = nil end
        whisperTask = nil
        hs.alert.closeAll()

        if wasCancelled then
            finishInteraction()
            showStatus("Cancelado", {red = 0.55, green = 0.18, blue = 0.14, alpha = 0.96}, 1.5)
            return
        end

        if code ~= 0 then
            finishInteraction()
            hs.alert.show("❌ Error Whisper: " .. (stderr or "desconocido"), 5)
            print("Whisper error: " .. (stderr or ""))
            return
        end

        local text
        local readOk, readErr = pcall(function()
            local f = assert(io.open("/tmp/voice_input.txt"), "no se encontró el archivo de salida")
            text = f:read("*a") or ""
            f:close()
            text = text:gsub("^%s*(.-)%s*$", "%1")
        end)

        local targetWindow = focusedWindow
        finishInteraction()

        if not readOk then
            hs.alert.show("❌ Error leyendo salida de Whisper", 3)
            print("Whisper post-processing error: " .. tostring(readErr))
            return
        end

        if text == "" then
            hs.alert.show("⚠️ No se detectó texto", 2)
            return
        end

        local pasteOk, pasteErr = pcall(function()
            hs.pasteboard.setContents(text)
            if targetWindow then targetWindow:focus() end
            hs.timer.doAfter(0.2, function()
                local strokeOk, strokeErr = pcall(function()
                    hs.eventtap.keyStroke({"cmd"}, "v")
                    local preview = text:len() > 60 and text:sub(1, 60) .. "…" or text
                    hs.alert.show("✅ " .. preview, 3)
                end)

                if not strokeOk then
                    print("Paste error: " .. tostring(strokeErr))
                    hs.alert.show("⚠️ Transcripto, pero no se pudo pegar", 3)
                end
            end)
        end)

        if not pasteOk then
            print("Whisper paste preparation error: " .. tostring(pasteErr))
            hs.alert.show("⚠️ Transcripto, pero falló el pegado automático", 3)
        end
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

    whisperTask = hs.task.new(whisperBin, onComplete, onStream, whisperArgs)
    local started = whisperTask and whisperTask:start()

    if not started then
        whisperTask = nil
        finishInteraction()
        hs.alert.show("❌ No se pudo iniciar Whisper", 3)
        return
    end

    -- Watchdog: si whisper se cuelga y onComplete nunca llega, limpiamos el estado.
    if whisperWatchdog then whisperWatchdog:stop() end
    whisperWatchdog = hs.timer.doAfter(120, function()
        whisperWatchdog = nil
        cancelRequested = true
        if whisperTask then whisperTask:terminate() end
        hs.alert.closeAll()
        hs.alert.show("⚠️ Whisper tardó demasiado, cancelando…", 3)
    end)
end

startTap()
hs.alert.show("Whisper listo ⚡ Command derecho para grabar", 3)
