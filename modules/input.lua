hl.config({
    input = {
        kb_layout    = "us",
        kb_options   = "", -- Normal Caps Lock behavior
        repeat_rate  = 40,
        repeat_delay = 250,

        follow_mouse = 1,
        sensitivity  = 0,

        touchpad = {
            natural_scroll = true,
            tap_to_click   = true,
            disable_while_typing = true,
        },
    },
})

-- 3-finger horizontal swipe changes workspace
hl.gesture({
    fingers   = 3,
    direction = "horizontal",
    action    = "workspace",
})
