-- Vesper look and feel: tinted glass, squircle corners, a soft glow that follows the wallpaper accent.
-- Colours come from generated/colors.lua (scripts/wallcolors.py); the defaults below are used until it runs.

local rice = os.getenv("HOME") .. "/.config/hypr-rice"
local pal = {
    accent = "c4a7ff", accent2 = "ff9fc4", overlay = "3a3548", mantle = "0d0b12", island = "08070b",
}
pcall(function()
    local ok, c = pcall(dofile, rice .. "/generated/colors.lua")
    if ok and type(c) == "table" then
        for k, v in pairs(c) do pal[k] = v end
    end
end)

-- 0xAARRGGBB number for shadows, "rgba(rrggbbaa)" string for borders
local function argb(hex, a) return tonumber(a .. hex, 16) or 0x66000000 end

hl.config({
    general = {
        gaps_in     = 5,
        gaps_out    = 12,
        border_size = 2,
        layout      = "dwindle",

        col = {
            active_border   = { colors = { "rgba(" .. pal.accent .. "f2)", "rgba(" .. pal.accent2 .. "f2)" }, angle = 45 },
            inactive_border = "rgba(" .. pal.overlay .. "55)",
        },

        resize_on_border = true,
        extend_border_grab_area = 18,
        allow_tearing    = false,
    },

    decoration = {
        rounding       = 18,
        rounding_power = 3.4,          -- 2 = plain circle corners, higher = squircle (phone-style)

        active_opacity   = 1.0,
        inactive_opacity = 0.95,

        dim_inactive = true,
        dim_strength = 0.10,

        -- A soft glow in the accent colour under the focused window, plain dark shadow under the rest.
        shadow = {
            enabled        = true,
            range          = 26,
            render_power   = 3,
            color          = argb(pal.accent, "40"),
            color_inactive = 0x55000000,
        },

        -- Blur is the costly part: size 8 / passes 3 is the sweet spot for glass, xray keeps the cost down
        -- (windows blur the wallpaper, not each other) and layer rules limit it to the shell surfaces.
        blur = {
            enabled           = true,
            size              = 8,
            passes            = 3,
            noise             = 0.015,
            contrast          = 1.0,
            brightness        = 0.92,
            vibrancy          = 0.22,
            vibrancy_darkness = 0.1,
            xray              = true,
            ignore_opacity    = true,
            new_optimizations = true,
            special           = false,
            popups            = false,
        },
    },

    misc = {
        disable_hyprland_logo        = true,
        disable_splash_rendering     = true,
        force_default_wallpaper      = 0,
        focus_on_activate            = true,
        mouse_move_enables_dpms      = true,
        key_press_enables_dpms       = true,
        animate_manual_resizes       = false,
        animate_mouse_windowdragging = false,
        font_family                  = "JetBrainsMono Nerd Font",
    },

    ecosystem = {
        no_update_news  = true,
        no_donation_nag = true,
    },

    -- Crisp XWayland apps at fractional scale (otherwise they are upscaled and blurry)
    xwayland = {
        force_zero_scaling = true,
    },

    cursor = {
        inactive_timeout = 5,   -- hide cursor after 5s idle
    },

    dwindle = {
        preserve_split = true,
    },

    master = {
        new_status = "master",
    },
})
