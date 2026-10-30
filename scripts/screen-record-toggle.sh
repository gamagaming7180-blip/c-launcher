#!/usr/bin/env bash
# Hypr Rice screen recorder.  status | toggle | menu | start [none|mic|sys|both] [region] | stop
#   toggle  start/stop, using the last audio choice (the Super+Alt+R bind keeps working)
#   menu    stop if recording, otherwise ask: Microphone / Laptop sound / Both / No audio (the bar's REC pill)
set -u

RUNTIME_BASE="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}"
STATE_DIR="$RUNTIME_BASE/hypr-rice-screenrecord-${UID:-$(id -u)}"
PID_FILE="$STATE_DIR/pid"
FILE_FILE="$STATE_DIR/file"
LOG_FILE="$STATE_DIR/wf-recorder.log"
AUDIO_FILE="$STATE_DIR/audio"      # last audio choice
MODS_FILE="$STATE_DIR/mods"        # pulse modules created for "both"
OUT_DIR="${HOME}/Videos/ScreenRecordings"
RICE="${HOME}/.config/hypr-rice"

mkdir -p "$STATE_DIR" 2>/dev/null || exit 1
chmod 700 "$STATE_DIR" 2>/dev/null || true

notify() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -a "Hypr Rice" -t 3500 "$1" "$2" >/dev/null 2>&1 || true
    fi
}

recording_pid() {
    [[ -r "$PID_FILE" ]] || return 1
    local pid comm stat
    pid="$(<"$PID_FILE")"
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    comm="$(ps -p "$pid" -o comm= 2>/dev/null | tr -d '[:space:]')"
    [[ "$comm" == "wf-recorder" ]] || return 1
    stat="$(ps -p "$pid" -o stat= 2>/dev/null | tr -d '[:space:]')"
    [[ "$stat" != Z* ]] || return 1
    printf '%s' "$pid"
}

clean_stale_state() {
    if [[ -e "$PID_FILE" ]] && ! recording_pid >/dev/null; then
        rm -f "$PID_FILE"
        teardown_mix
    fi
    if [[ ! -e "$PID_FILE" ]]; then
        rm -f "$FILE_FILE"
    fi
}

json_status() {
    local mode="$1" text tooltip
    case "$mode" in
        recording)
            text='■ STOP'
            tooltip="Recording is active. Click to stop and save the MP4. Shortcut: Super+Alt+R."
            ;;
        missing)
            text='● REC'
            tooltip='wf-recorder is not installed. Install on CachyOS: sudo pacman -S wf-recorder'
            ;;
        *)
            text='● REC'
            tooltip='Start screen recording (choose mic, laptop sound or both). Click again or press Super+Alt+R to stop.'
            ;;
    esac
    printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' \
        "$text" "$mode" "$tooltip"
}

# ---------------------------------------------------------------- audio
teardown_mix() {
    [[ -r "$MODS_FILE" ]] || return 0
    local m
    for m in $(tac "$MODS_FILE" 2>/dev/null); do
        pactl unload-module "$m" >/dev/null 2>&1 || true
    done
    rm -f "$MODS_FILE"
}

# prints the pulse/pipewire source to record, or nothing
audio_source() {
    local mode="$1" mic sink id
    command -v pactl >/dev/null 2>&1 || return 0
    mic="$(pactl get-default-source 2>/dev/null)"
    sink="$(pactl get-default-sink 2>/dev/null)"
    case "$mode" in
        mic)  printf '%s' "$mic" ;;
        sys)  [[ -n "$sink" ]] && printf '%s.monitor' "$sink" ;;
        both)
            if [[ -z "$mic" || -z "$sink" ]]; then
                [[ -n "$sink" ]] && printf '%s.monitor' "$sink" || printf '%s' "$mic"
                return 0
            fi
            : > "$MODS_FILE"
            for spec in \
                "module-null-sink sink_name=hypr_rec_mix sink_properties=device.description=RecordingMix" \
                "module-loopback source=$mic sink=hypr_rec_mix latency_msec=40" \
                "module-loopback source=${sink}.monitor sink=hypr_rec_mix latency_msec=40"; do
                # shellcheck disable=SC2086
                id="$(pactl load-module $spec 2>/dev/null)"
                if [[ ! "$id" =~ ^[0-9]+$ ]]; then
                    teardown_mix
                    printf '%s.monitor' "$sink"
                    return 0
                fi
                printf '%s\n' "$id" >> "$MODS_FILE"
            done
            printf 'hypr_rec_mix.monitor'
            ;;
    esac
}

valid_mode() { [[ "$1" == none || "$1" == mic || "$1" == sys || "$1" == both ]]; }
last_mode() { local m; m="$(cat "$AUDIO_FILE" 2>/dev/null)"; valid_mode "$m" && printf '%s' "$m" || printf 'none'; }

# ---------------------------------------------------------------- record
start_recording() {
    local mode="${1:-none}" region="${2:-}"
    valid_mode "$mode" || mode=none
    if ! command -v wf-recorder >/dev/null 2>&1; then
        notify "Screen recording unavailable" "Install it with: sudo pacman -S wf-recorder"
        return 1
    fi
    if [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
        notify "Screen recording unavailable" "This needs to run inside your Wayland session."
        return 1
    fi

    mkdir -p "$OUT_DIR" || {
        notify "Screen recording failed" "Could not create $OUT_DIR"
        return 1
    }
    local stamp file pid dev="" geo=""
    local -a args=()
    stamp="$(date +%F_%H-%M-%S)"
    file="$OUT_DIR/ScreenRecording_${stamp}.mp4"
    local n=1
    while [[ -e "$file" ]]; do
        file="$OUT_DIR/ScreenRecording_${stamp}_${n}.mp4"
        n=$((n + 1))
    done

    if [[ "$region" == region ]]; then
        if ! command -v slurp >/dev/null 2>&1; then
            notify "Screen recording" "Region needs slurp: sudo pacman -S slurp"
            return 1
        fi
        geo="$(slurp 2>/dev/null)" || true
        [[ -n "$geo" ]] || return 1
        args+=(-g "$geo")
    fi

    printf '%s\n' "$mode" > "$AUDIO_FILE"
    if [[ "$mode" != none ]]; then
        dev="$(audio_source "$mode")"
        if [[ -n "$dev" ]]; then
            args+=("--audio=$dev")
        else
            notify "Screen recording" "No audio device found, recording without sound."
        fi
    fi

    : > "$LOG_FILE"
    chmod 600 "$LOG_FILE" 2>/dev/null || true
    wf-recorder "${args[@]}" -f "$file" >"$LOG_FILE" 2>&1 &
    pid=$!
    printf '%s\n' "$pid" > "$PID_FILE"
    printf '%s\n' "$file" > "$FILE_FILE"
    chmod 600 "$PID_FILE" "$FILE_FILE" 2>/dev/null || true
    sleep 0.35

    if recording_pid >/dev/null; then
        case "$mode" in
            mic)  dev="with microphone" ;;
            sys)  dev="with laptop sound" ;;
            both) dev="with microphone + laptop sound" ;;
            *)    dev="without audio" ;;
        esac
        notify "Screen recording started" "Recording $dev. Click ■ STOP or press Super+Alt+R to finish."
        return 0
    fi

    local details
    details="$(tail -n 3 "$LOG_FILE" 2>/dev/null | tr '\n' ' ' | cut -c1-260)"
    rm -f "$PID_FILE" "$FILE_FILE"
    teardown_mix
    notify "Screen recording failed to start" "${details:-wf-recorder exited immediately. Check the installed wf-recorder package and Hyprland logs.}"
    return 1
}

stop_recording() {
    local pid file i
    pid="$(recording_pid 2>/dev/null || true)"
    if [[ -z "$pid" ]]; then
        clean_stale_state
        return 0
    fi
    file="$(cat "$FILE_FILE" 2>/dev/null || true)"
    kill -INT "$pid" 2>/dev/null || true
    for i in {1..50}; do
        if ! recording_pid >/dev/null; then
            break
        fi
        sleep 0.1
    done
    if recording_pid >/dev/null; then
        notify "Finalizing screen recording" "The recorder is still closing the video file. It will be saved to Videos/ScreenRecordings."
        return 0
    fi
    rm -f "$PID_FILE" "$FILE_FILE"
    teardown_mix
    if [[ -n "$file" && -s "$file" ]]; then
        notify "Screen recording saved" "${file/#$HOME/~}"
    else
        notify "Screen recording stopped" "The recorder stopped; check $OUT_DIR if you don't see the video."
    fi
    return 0
}

# ---------------------------------------------------------------- the choice menu
choose_audio() {
    local items="Microphone\nLaptop sound\nMicrophone + laptop sound\nNo audio" pick
    local -a ropts=(-dmenu -i -no-custom -p "Record")
    [[ -f "$RICE/rofi/config.rasi" ]] && ropts=(-config "$RICE/rofi/config.rasi" "${ropts[@]}")
    [[ -f "$RICE/rofi/catppuccin.rasi" ]] && ropts+=(-theme "$RICE/rofi/catppuccin.rasi")
    if ! command -v rofi >/dev/null 2>&1; then
        last_mode; return 0                       # no rofi: just use the last choice
    fi
    pick="$(printf '%b\n' "$items" | rofi "${ropts[@]}" 2>/dev/null)" || return 1
    case "$pick" in
        "Microphone")                 printf 'mic' ;;
        "Laptop sound")               printf 'sys' ;;
        "Microphone + laptop sound")  printf 'both' ;;
        "No audio")                   printf 'none' ;;
        *) return 1 ;;
    esac
}

case "${1:-toggle}" in
    status)
        if recording_pid >/dev/null; then
            json_status recording
        elif command -v wf-recorder >/dev/null 2>&1; then
            clean_stale_state
            json_status idle
        else
            json_status missing
        fi
        ;;
    toggle)
        if recording_pid >/dev/null; then
            stop_recording
        else
            clean_stale_state
            start_recording "$(last_mode)"
        fi
        ;;
    menu)
        if recording_pid >/dev/null; then
            stop_recording
        else
            clean_stale_state
            mode="$(choose_audio)" || exit 0     # menu dismissed: do nothing
            start_recording "$mode"
        fi
        ;;
    start)
        if recording_pid >/dev/null; then
            exit 0
        fi
        clean_stale_state
        start_recording "${2:-none}" "${3:-}"
        ;;
    stop)
        stop_recording
        ;;
    *)
        echo "Usage: $0 {status|toggle|menu|start [none|mic|sys|both] [region]|stop}" >&2
        exit 2
        ;;
esac
