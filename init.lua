local recording = false
local recordingTask = nil
local tap = nil
local animFrame = 0
local focusedWindow = nil

local function startTap()
    if tap then tap:stop() end
    tap = hs.eventtap.new({hs.eventtap.event.types.flagsChanged}, function(event)
        local keyCode = event:getKeyCode()
        if keyCode ~= 54 then return false end
        local flags = event:getFlags()

        if not flags.cmd then
            if not recording then
                focusedWindow = hs.window.focusedWindow()
                recording = true
                os.remove("/tmp/voice_input.wav")
                os.remove("/tmp/voice_input.txt")
                hs.alert.show("🔴 Grabando...", 999)
                recordingTask = hs.task.new("/opt/homebrew/bin/sox", nil, {"-d", "/tmp/voice_input.wav"})
                recordingTask:start()
            else
                recording = false
                hs.alert.closeAll()
                if recordingTask then
                    recordingTask:terminate()
                    recordingTask = nil
                end
                hs.alert.show("Transcribiendo...", 30)
                hs.task.new("/Users/am/Library/Python/3.9/bin/whisper", function(code, stdout, stderr)
                    hs.alert.closeAll()
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
                                hs.alert.show("OK: " .. text, 4)
                            end)
                        else
                            hs.alert.show("No se detecto texto", 2)
                        end
                    else
                        hs.alert.show("Error leyendo transcripcion", 2)
                    end
                    os.remove("/tmp/voice_input.wav")
                    os.remove("/tmp/voice_input.txt")
                    hs.timer.doAfter(0.3, startTap)
                end, {"/tmp/voice_input.wav", "--language", "Spanish", "--model", "medium", "--output_format", "txt", "--output_dir", "/tmp"}):start()
            end
        end

        return false
    end)
    tap:start()
end

startTap()
hs.alert.show("Whisper listo - Command derecho para grabar", 3)
