#!/usr/bin/env bash
# fingerprint.sh: get the fingerprint reader working and use it for the lock screen,
# authorization pop-ups (polkit) and, if you want, sudo. Your password always still works.
#
#   fingerprint.sh              same as "doctor"
#   fingerprint.sh doctor       find out what is wrong / what is already working
#   fingerprint.sh setup        guided: install, enroll, test, switch on
#   fingerprint.sh enroll [finger]   add one finger (default right-index-finger)
#   fingerprint.sh verify       test your finger right now
#   fingerprint.sh reset        delete saved prints (fixes "it stopped scanning" most of the time)
#   fingerprint.sh lock|polkit|sudo  on|off     choose where the fingerprint is accepted
set -u
RICE="$HOME/.config/hypr-rice"
PAM_DIR="${FP_PAM_DIR:-/etc/pam.d}"
SUDO="${FP_SUDO-sudo}"
TAG="# hypr-rice-fingerprint"
ME="${USER:-$(id -un)}"

G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; C=$'\e[36m'; B=$'\e[1m'; D=$'\e[2m'; N=$'\e[0m'
ok()   { echo " ${G}✔${N} $*"; }
bad()  { echo " ${R}✘${N} $*"; }
warn() { echo " ${Y}!${N} $*"; }
say()  { echo " ${C}›${N} $*"; }
head_() { echo; echo "${B}$*${N}"; }
ask()  { local a; read -rp " ${C}?${N} $1 [y/N] " a; [[ "$a" =~ ^[Yy] ]]; }
notify() { command -v notify-send >/dev/null && notify-send -t 4000 "Fingerprint" "$1" 2>/dev/null; true; }

# ------------------------------------------------------------------ hardware
VENDORS="27c6:Goodix 06cb:Synaptics 138a:Validity 04f3:Elan 147e:Upek 10a5:FPC 1c7a:LighTuning 0483:STMicro 0a5c:Broadcom"

readers() {   # prints "vid:pid  description" for USB devices from fingerprint-sensor makers
    local d v p name
    for d in /sys/bus/usb/devices/*; do
        [ -r "$d/idVendor" ] || continue
        v=$(<"$d/idVendor"); p=$(<"$d/idProduct")
        for pair in $VENDORS; do
            if [ "${pair%%:*}" = "$v" ]; then
                name=$(cat "$d/product" 2>/dev/null || echo "?")
                echo "$v:$p  ${pair#*:}  ($name)  [$d]"
            fi
        done
    done
}

have_fprintd() { command -v fprintd-enroll >/dev/null 2>&1; }

fp_list() { fprintd-list "$ME" 2>&1; }

device_count() { fp_list | grep -oE 'found [0-9]+ device' | grep -oE '[0-9]+' | head -1; }

enrolled() { fp_list | grep -E '^ *- #[0-9]+:' | sed -E 's/^ *- #[0-9]+: *//'; }

# ------------------------------------------------------------------ doctor
doctor() {
    head_ "Fingerprint check-up"
    local bad_n=0

    head_ "1. The reader"
    local r; r=$(readers)
    if [ -n "$r" ]; then
        echo "$r" | while read -r line; do ok "USB: $line"; done
    else
        bad "no USB fingerprint sensor found. Check: ${D}lsusb${N}  (if your reader is there, tell me the line)"
        bad_n=1
    fi

    head_ "2. Software"
    if have_fprintd; then
        local ver; ver=$(pacman -Q fprintd 2>/dev/null | cut -d' ' -f2)
        ok "fprintd installed${ver:+ (version $ver)}"
        [ -e /usr/lib/security/pam_fprintd.so ] && ok "pam_fprintd present" || warn "pam_fprintd.so not in /usr/lib/security"
        local n; n=$(device_count)
        if [ "${n:-0}" -ge 1 ]; then
            ok "fprintd can see the reader (${n} device)"
        else
            bad "fprintd cannot see a reader. Output was:"; fp_list | sed 's/^/      /'
            say "That means this sensor model is not supported by libfprint yet, or the service is stuck."
            say "Try: ${D}sudo systemctl restart fprintd${N}  then run this again."
            bad_n=1
        fi
        local f; f=$(enrolled)
        if [ -n "$f" ]; then ok "saved fingers: $(echo "$f" | tr '\n' ',' | sed 's/,$//;s/,/, /g')"
        else warn "no fingers enrolled yet. Run: ${D}fingerprint.sh setup${N}"; fi
    else
        bad "fprintd is not installed. Run: ${D}fingerprint.sh setup${N}  (or: sudo pacman -S fprintd)"
        bad_n=1
    fi

    head_ "3. Where it is switched on"
    grep -q "HYPR_RICE_FINGERPRINT_BEGIN" "$RICE/hyprlock.conf" 2>/dev/null && ok "lock screen" || warn "lock screen: off"
    grep -qs pam_fprintd "$PAM_DIR/polkit-1" && ok "authorization pop-ups (polkit)" || warn "authorization pop-ups: off"
    grep -qs pam_fprintd "$PAM_DIR/sudo" && ok "sudo" || echo " ${D}- sudo: off (optional)${N}"

    # Sensors that nap and never wake up are a classic reason for "it stopped scanning".
    local d
    for d in /sys/bus/usb/devices/*; do
        [ -r "$d/idVendor" ] || continue
        for pair in $VENDORS; do
            [ "${pair%%:*}" = "$(<"$d/idVendor")" ] || continue
            if [ "$(cat "$d/power/control" 2>/dev/null)" = "auto" ] && [ "$(cat "$d/power/runtime_status" 2>/dev/null)" = "suspended" ]; then
                head_ "4. Power saving"
                warn "the sensor is asleep (USB autosuspend). If it stops responding, a udev rule can keep it awake: tell me and I will write it."
            fi
        done
    done
    echo
    [ "$bad_n" = 0 ] && say "Looks healthy. Test it: ${D}fingerprint.sh verify${N}" || say "Fix the red items above, then run the check-up again."
}

# ------------------------------------------------------------------ enrolling
FINGERS=(right-index-finger left-index-finger right-thumb left-thumb right-middle-finger)

enroll_one() {
    local f="${1:-right-index-finger}"
    echo
    say "Enrolling ${B}$f${N}. Touch the sensor with that finger, lift, and repeat a few times."
    say "Tip: change the angle a little each time, covering the tip, the sides and the pad."
    if fprintd-enroll -f "$f" "$ME"; then
        ok "saved ${f}"
        notify "Saved $f"
        return 0
    fi
    bad "enrolling $f did not finish (try again, a slightly firmer, flatter touch works best)"
    return 1
}

verify() {
    echo
    say "Touch the sensor now..."
    local out; out=$(fprintd-verify "$ME" 2>&1); echo "$out" | sed 's/^/   /'
    if echo "$out" | grep -q "verify-match"; then
        ok "${G}match!${N} It knows you. 🎉"; notify "Fingerprint matched 🎉"; return 0
    fi
    bad "no match. If this keeps happening: ${D}fingerprint.sh reset${N} then ${D}fingerprint.sh setup${N}"
    return 1
}

reset_prints() {
    if ! have_fprintd; then bad "fprintd is not installed"; return 1; fi
    ask "Delete all saved fingerprints for $ME and start fresh?" || return 1
    fprintd-delete "$ME" && ok "old prints deleted"
}

# ------------------------------------------------------------------ PAM switches
pam_on() {   # $1 = file name in /etc/pam.d
    local f="$PAM_DIR/$1" tmp
    [ -f "$f" ] || { bad "$f not found; skipped"; return 1; }
    if grep -q pam_fprintd "$f"; then ok "$1 already accepts fingerprint"; return 0; fi
    if [ -z "${FP_PAM_DIR:-}" ] && [ ! -e /usr/lib/security/pam_fprintd.so ]; then
        bad "pam_fprintd.so is missing. Install fprintd first."; return 1
    fi
    tmp=$(mktemp)
    awk -v line="auth      sufficient   pam_fprintd.so max-tries=1 timeout=10 $TAG" \
        'NR==1 && /^#%PAM/ {print; print line; next} NR==1 {print line} {print}' "$f" > "$tmp"
    $SUDO cp -n "$f" "$f.hypr-rice.bak" 2>/dev/null
    $SUDO install -m 644 "$tmp" "$f" && ok "$1: fingerprint accepted (password still works)" || bad "could not write $f"
    rm -f "$tmp"
}

pam_off() {
    local f="$PAM_DIR/$1"
    [ -f "$f" ] || return 0
    if grep -q "$TAG\$" "$f"; then
        $SUDO sed -i "/$TAG\$/d" "$f" && ok "$1: fingerprint removed"
    else
        ok "$1: nothing of ours to remove"
    fi
}

switch() {   # $1 = lock|polkit|sudo   $2 = on|off
    case "$1" in
        lock)   python3 "$RICE/scripts/fingerprint-lock.py" "$2" ;;
        polkit) [ "$2" = on ] && pam_on polkit-1 || pam_off polkit-1 ;;
        sudo)   [ "$2" = on ] && pam_on sudo || pam_off sudo ;;
        *) echo "unknown target: $1"; return 1 ;;
    esac
}

# ------------------------------------------------------------------ guided setup
setup() {
    cat <<EOF

${B}   ☝  Fingerprint setup${N}
   ${D}install → enroll → test → switch on. Takes about two minutes.${N}
EOF
    head_ "Step 1: software"
    if have_fprintd; then ok "fprintd is already installed"
    else
        say "Installing fprintd (needs your password once)..."
        $SUDO pacman -S --needed fprintd || { bad "install failed"; return 1; }
    fi
    $SUDO systemctl restart fprintd 2>/dev/null || true

    head_ "Step 2: is the reader visible?"
    local n; n=$(device_count)
    if [ "${n:-0}" -lt 1 ]; then
        bad "fprintd cannot see a fingerprint reader."
        readers | sed 's/^/   /'
        say "If a sensor is listed above, its model probably isn't supported by libfprint yet."
        say "Send me that line (the ID like 27c6:xxxx) and I will check for a driver or workaround."
        return 1
    fi
    ok "reader found"

    head_ "Step 3: fresh start?"
    if [ -n "$(enrolled)" ]; then
        say "Saved fingers: $(enrolled | tr '\n' ' ')"
        say "If it 'stopped scanning', old prints are the usual cause."
        ask "Delete them and enroll again?" && fprintd-delete "$ME" >/dev/null && ok "cleared"
    else
        ok "nothing saved yet"
    fi

    head_ "Step 4: enroll your fingers"
    if [ -z "$(enrolled)" ]; then
        enroll_one right-index-finger || return 1
        ask "Add a second finger as backup (recommended)?" && enroll_one left-index-finger
        ask "And a thumb?" && enroll_one right-thumb
    else
        ok "already enrolled"
    fi

    head_ "Step 5: test it"
    verify || { warn "fix the match first, then run: fingerprint.sh setup"; return 1; }

    head_ "Step 6: switch it on"
    switch lock on
    switch polkit on
    if ask "Also use fingerprint for sudo in the terminal? (it waits ~10s for a finger, then asks the password)"; then
        switch sudo on
    fi
    cat <<EOF

${G}${B}   All set! ✨${N}
   Lock screen: ${B}SUPER+L${N}, then touch the sensor.
   Pop-up authorizations: touch the sensor instead of typing.
   Undo anything with: ${D}fingerprint.sh lock|polkit|sudo off${N}
EOF
    notify "Fingerprint is ready ✨"
}

case "${1:-doctor}" in
    doctor)  doctor ;;
    setup)   setup ;;
    enroll)  have_fprintd || { bad "install fprintd first: fingerprint.sh setup"; exit 1; }; enroll_one "${2:-right-index-finger}" ;;
    verify)  have_fprintd || { bad "install fprintd first: fingerprint.sh setup"; exit 1; }; verify ;;
    reset)   reset_prints ;;
    lock|polkit|sudo) [ "${2:-}" = on ] || [ "${2:-}" = off ] || { echo "usage: fingerprint.sh $1 on|off"; exit 1; }; switch "$1" "$2" ;;
    -h|--help|help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' ;;
    *) echo "unknown command: $1 (try: doctor, setup, enroll, verify, reset, lock|polkit|sudo on|off)"; exit 1 ;;
esac
