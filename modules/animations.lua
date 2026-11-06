-- Vesper motion: springy windows, long-tailed expo easing for everything else.
-- speed is in deciseconds (4 = 400ms). Nothing loops (no border-angle spin), so an idle desktop costs nothing.

hl.config({ animations = { enabled = true } })

hl.curve("expo",   { type = "bezier", points = { {0.16, 1},   {0.30, 1}   } })   -- easeOutExpo: fast start, long soft landing
hl.curve("smooth", { type = "bezier", points = { {0.40, 0},   {0.20, 1}   } })   -- material standard
hl.curve("back",   { type = "bezier", points = { {0.34, 1.45},{0.64, 1}   } })   -- tiny overshoot
hl.curve("linear", { type = "bezier", points = { {0, 0},      {1, 1}      } })
hl.curve("pop",    { type = "spring", mass = 1, stiffness = 120, dampening = 15 })

hl.animation({ leaf = "global",           enabled = true, speed = 8,   bezier = "default" })
hl.animation({ leaf = "border",           enabled = true, speed = 6,   bezier = "expo" })
hl.animation({ leaf = "windows",          enabled = true, speed = 4,   spring = "pop" })
hl.animation({ leaf = "windowsIn",        enabled = true, speed = 4,   spring = "pop",    style = "popin 82%" })
hl.animation({ leaf = "windowsOut",       enabled = true, speed = 2.5, bezier = "smooth", style = "popin 90%" })
hl.animation({ leaf = "windowsMove",      enabled = true, speed = 4,   spring = "pop" })
hl.animation({ leaf = "fade",             enabled = true, speed = 3,   bezier = "smooth" })
hl.animation({ leaf = "fadeIn",           enabled = true, speed = 3,   bezier = "smooth" })
hl.animation({ leaf = "fadeOut",          enabled = true, speed = 2,   bezier = "linear" })
hl.animation({ leaf = "layers",           enabled = true, speed = 4,   bezier = "expo" })
hl.animation({ leaf = "layersIn",         enabled = true, speed = 4,   bezier = "back",   style = "popin 92%" })
hl.animation({ leaf = "layersOut",        enabled = true, speed = 2.5, bezier = "smooth", style = "popin 94%" })
hl.animation({ leaf = "workspaces",       enabled = true, speed = 4,   bezier = "expo",   style = "slidefade 22%" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 4,   bezier = "expo",   style = "slidefadevert 18%" })
