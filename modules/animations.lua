-- Animations: short, snappy, spring-based for windows.
-- speed is in deciseconds (4 = 400ms). Everything is kept <= ~0.4s so the
-- desktop feels fast and the GPU spends less time animating.

hl.config({ animations = { enabled = true } })

hl.curve("out",     { type = "bezier", points = { {0.23, 1},    {0.32, 1}   } })  -- easeOutQuint
hl.curve("smooth",  { type = "bezier", points = { {0.65, 0.05}, {0.36, 1}   } })  -- easeInOutCubic
hl.curve("linear",  { type = "bezier", points = { {0, 0},       {1, 1}      } })
hl.curve("quick",   { type = "bezier", points = { {0.15, 0},    {0.1, 1}    } })
hl.curve("pop",     { type = "spring", mass = 1, stiffness = 90, dampening = 16 })

hl.animation({ leaf = "global",        enabled = true, speed = 8,   bezier = "default" })
hl.animation({ leaf = "border",        enabled = true, speed = 5,   bezier = "out" })
hl.animation({ leaf = "windows",       enabled = true, speed = 4,   spring = "pop" })
hl.animation({ leaf = "windowsIn",     enabled = true, speed = 4,   spring = "pop",    style = "popin 88%" })
hl.animation({ leaf = "windowsOut",    enabled = true, speed = 2,   bezier = "linear", style = "popin 90%" })
hl.animation({ leaf = "fade",          enabled = true, speed = 3,   bezier = "quick" })
hl.animation({ leaf = "layers",        enabled = true, speed = 3.5, bezier = "out" })
hl.animation({ leaf = "layersIn",      enabled = true, speed = 4,   bezier = "out",    style = "slide" })
hl.animation({ leaf = "layersOut",     enabled = true, speed = 2,   bezier = "linear", style = "slide" })
hl.animation({ leaf = "workspaces",    enabled = true, speed = 3.5, bezier = "out",    style = "slide" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3.5, bezier = "out", style = "slidevert" })

-- The shadow/border "angle" animations loop forever and force constant redraws.
-- Left off on purpose: they cost battery for no real benefit.
