-- Look and feel. Palette: Catppuccin Mocha.
--   mauve cba6f7  blue 89b4fa  lavender b4befe  surface0 313244  base 1e1e2e

hl.config({
    general = {
        gaps_in     = 4,
        gaps_out    = 10,
        border_size = 2,
        layout      = "dwindle",

        col = {
            active_border   = { colors = { "rgba(cba6f7ee)", "rgba(89b4faee)" }, angle = 45 },
            inactive_border = "rgba(313244aa)",
        },

        resize_on_border = true,   -- drag borders/gaps to resize
        allow_tearing    = false,
    },

    decoration = {
        rounding       = 12,
        rounding_power = 2,

        active_opacity   = 1.0,
        inactive_opacity = 1.0,

        -- Soft, small shadow. Cheap, and gives depth.
        shadow = {
            enabled      = true,
            range        = 12,
            render_power = 3,
            color        = 0x66000000,
        },

        -- Blur is the single most expensive eye-candy. These values are the
        -- sweet spot: size 5 / passes 2 looks smooth, xray + ignore_opacity
        -- keep the cost low, and blur only applies where a rule asks for it.
        blur = {
            enabled          = true,
            size             = 5,
            passes           = 2,
            noise            = 0.01,
            contrast         = 0.95,
            brightness       = 0.9,
            vibrancy         = 0.17,
            xray             = true,
            ignore_opacity   = true,
            new_optimizations = true,
            special          = false,
            popups           = false,
        },
    },

    misc = {
        disable_hyprland_logo   = true,
        disable_splash_rendering = true,
        force_default_wallpaper = 0,
        focus_on_activate       = true,
        mouse_move_enables_dpms = true,
        key_press_enables_dpms  = true,
        animate_manual_resizes  = false,
        animate_mouse_windowdragging = false,
    },

    ecosystem = {
        no_update_news  = true,
        no_donation_nag = true,
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
