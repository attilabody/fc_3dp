# pi02w_case.py walkthrough

How [pi02w_case.py](pi02w_case.py) is organised, top to bottom. The script runs in a straight line with no
classes: it defines the parameters, sets up some helper functions, builds the model body by body, checks it, then
saves and exports.

Project status and design history are in [AGENTS.md](AGENTS.md).

## Running the script

**Requirements:** FreeCAD 1.1.x (tested with 1.1.4). The script uses only FreeCAD's own Python modules, so there's
nothing else to install.

The script writes all output next to itself, whatever directory you run it from:

| File | Content |
|---|---|
| `pi02w_case.FCStd` | The parametric FreeCAD model |
| `pi02w_case.step` | Base and lid as exact solids, for the slicer or other CAD tools |
| `pi02w_case_base.stl` | *Only with `EXPORT_STL=1`:* base, in print orientation |
| `pi02w_case_lid.stl` | *Only with `EXPORT_STL=1`:* lid, already flipped top-down for printing |

Existing files are overwritten. For mesh output (e.g. Cura), prefix the build command:
`EXPORT_STL=1 QT_QPA_PLATFORM=offscreen freecad pi02w_case.py`.

### Normal build (recommended)

```sh
QT_QPA_PLATFORM=offscreen freecad pi02w_case.py
```

This starts the full FreeCAD application without opening a window. It's the only mode that can save display
settings, so the `.FCStd` opens with Base and Lid shown at 50 % transparency and the helpers hidden. The script
quits FreeCAD by itself when it's done.

The check results don't appear in the terminal in this mode (see the next section).

### Geometry and checks only

```sh
freecadcmd pi02w_case.py
```

This is FreeCAD's command-line version. It builds the same geometry and prints the check results to the terminal:

```text
Invalid objects: []
Base: valid=True solids=1 vol=11163 bbox=...
Lid: valid=True solids=1 vol=4701 bbox=...
Interference Lid x PCB: 8.086 mm3      <- expected: the intended clamp at the 4 posts
Base x Lid overlap: 0.0
Done
```

Any other `Interference ...` line, a non-empty `Invalid objects` list or `Sketch solve problem` means something is
wrong. This mode can't store display settings, so the `.FCStd` opens with everything at default visibility and no
transparency.

To see the checks *and* get a nicely displayed file, run `freecadcmd` first, then the normal build.

### From inside FreeCAD

Open the FreeCAD Python console (View → Panels → Python console) and run:

```python
p = "/path/to/pi02w_case.py"
exec(open(p).read(), {"__file__": p, "__name__": "__main__"})
```

Pass `__file__` exactly like this. The script uses it to find its output folder, and a plain
`exec(open(p).read())` silently writes the outputs somewhere else.

The model is built in a new document and saved over `pi02w_case.FCStd`. FreeCAD keeps running. The automatic quit
only happens in the headless build.

### Changing dimensions

There are two ways, and they don't mix:

- **Edit `PARAMS` in the script and re-run it.** Everything is regenerated: the model and the STEP (and the
  STLs, if enabled).
- **Edit the `Params` spreadsheet in the saved `.FCStd`** in FreeCAD and recompute. Then export the STEP yourself.

Re-running the script **overwrites** the `.FCStd`, so changes made only in the spreadsheet are lost. If you want to
keep a spreadsheet change, copy the value back into `PARAMS`.

### Housekeeping

Each run that overwrites the `.FCStd` may leave a `pi02w_case.<timestamp>.FCBak` backup, depending on FreeCAD's
backup settings. Python may also create a `__pycache__` folder. Both are safe to delete.

## 1. Parameters ([lines 38–160](pi02w_case.py#L38-L160))

`PARAMS` is a single list that holds every dimension. Each entry has one of two shapes:

- `("# Section title",)` becomes a bold heading row in the spreadsheet.
- `(alias, value, comment)` is one parameter. If the value is a string starting with `=`, it's a formula, for
  example `("z_bt", "=so_h + board_t", ...)`.

The list feeds two places:

- **The FreeCAD spreadsheet** `Params`, created by `make_sheet()`. Alias in column B, comment in column C, and
  formula rows stay live formulas.
- **A Python copy**, `P` ([line 142](pi02w_case.py#L142)). Each formula is evaluated in list order, so a derived
  value may only refer to parameters above it.

Two small helpers connect the two:

- `ex("z_bt + pin_proj")` → `"Params.z_bt + Params.pin_proj"`. It rewrites a Python-style formula into a FreeCAD
  expression, so the model stays linked to the spreadsheet.
- `nv("z_bt + pin_proj")` → `6.55`. It evaluates the same formula in Python. That number is the starting value
  FreeCAD gets when a feature is created; the expression then keeps it in sync.

Almost every helper below takes formula strings and calls both: `nv()` for the starting value and `ex()` for the
live link.

## 2. Sketch and feature helpers ([lines 165–359](pi02w_case.py#L165-L359))

### Sketch placement

- `sketch(body, name, role, offset)` attaches a sketch to one of the body's origin planes. The offset along the
  plane's normal is an expression, which is how you get a sketch at a height such as `z_ceil`.
- The XZ_Plane's normal points to −Y, so XZ sketches use `offset="-y"`.

### Constrained geometry

Every sketch these helpers create is fully constrained, with all positions driven by the spreadsheet.

- `fix_point()` pins a sketch point with a signed DistanceX/DistanceY constraint from the origin. It names the
  constraint (`tag_u` / `tag_v`) and attaches the expression to it. Every other shape helper is built on this.
- `polygon()` is a closed polyline: each corner is pinned by `fix_point`, with coincident constraints joining the
  segments.
- `rect()` is a 4-point polygon.
- `rounded_rect()` is 4 lines and 4 arcs, joined with endpoint-tangent constraints. The corner centres and radii
  are driven by expressions, which pins all its degrees of freedom.
- `circle_at()` is a circle with its centre and diameter driven by expressions.

### Skeleton link

- `circles_on_holes()` adds the 4 mounting-hole circles from the binder as external geometry. It then draws a
  circle concentric with each one at the requested diameter.
- `hole_edges()` finds which of the binder's edges are those holes, by matching their diameter to `hole_d`.

### Feature wrappers

- `pad()`, `pad_mid()` and `pocket()` wrap PartDesign Pad and Pocket. The length goes in as an expression, and
  there are options for reversed direction, symmetric (`SideType`), through-all and taper angle.
- `linear_pattern()` creates a pattern whose occurrence count and total length come from expressions. It sets the
  pattern as the body's **Tip** explicitly, because FreeCAD doesn't do that for patterns created by script.
- `binder()` creates a SubShapeBinder of another object.
- `box()` creates an AdditiveBox attached to the XY plane. It has to be attached, otherwise its AttachmentOffset
  is ignored.

## 3. The model

### Skeleton ([lines 367–385](pi02w_case.py#L367-L385))

- A `Skeleton` body containing `MasterSketch`.
- It holds the board outline, the 4 mounting-hole circles and the GPIO header rectangle.
- It also has short marker lines at the HDMI, USB and SD positions. These are only reference marks in the GUI; no
  feature uses them.

### PortCutters ([lines 387–409](pi02w_case.py#L387-L409))

- A separate body with three AdditiveBoxes: HDMI, the merged USB opening and the SD notch. Each runs from outside
  the wall up through the top of the lid.
- `port_cut(body)` subtracts these from a body. It gives each body its own binder of the cutters, because one
  object can belong to only one Boolean.

### Base ([lines 411–481](pi02w_case.py#L411-L481))

| Step | Feature | What it does |
|---|---|---|
| 1 | `Shell` | Outer rounded rectangle, from under the floor up to the shoulder height `z_r` |
| 2 | `Flange` | Full-width plate, longer than the shell by `flange_L` at each end |
| 3 | `Lip` | Thinner rounded rectangle above the shoulder, which the lid's outer wall slides over |
| 4 | `Cavity` | Pocket that hollows the inside, cutting upward through everything from the floor surface |
| 5 | `Standoffs`, `Pins`, `PinTips` | Circles on the skeleton holes. The tips are a short pad with a negative taper angle, which narrows them |
| 6 | `Ridge*` | Snap ridges. `ridge_profile()` gives a 4-point cross-section with a flat-ish catch at the bottom and a slope on top for the lid to slide over, padded symmetrically to `ridge_len` |
| 7 | `MountHoles` | Two through-holes in the flange (`mount_x0`, `mount_x1`, `mount_y`) |
| 8 | `PortCutouts` | Subtracts PortCutters |
| 9 | `IntakesBack` | One slot pocket through the back wall, repeated by a linear pattern |

### Lid ([lines 483–546](pi02w_case.py#L483-L546))

| Step | Feature | What it does |
|---|---|---|
| 1 | `LidBlock` | Solid rounded block from just above the shoulder (`z_r + skirt_gap`) to `z_top` |
| 2 | `LidHollow` | Pocket from the ceiling downward, leaving the top plate and the outer wall |
| 3 | `ClampPosts` | Pad downward from the ceiling, ending `clamp` below the PCB top |
| 4 | `PinReceivers` | Blind holes cut upward from the post ends |
| 5 | `GpioOpening` | Through-pocket in the top plate over the header |
| 6 | `Win*` | Snap windows: pockets centred on the lid's wall thickness and cut symmetrically through it, positioned to match the base ridges. They extend `win_clr` beyond each ridge end and above its top; the bottom edge sits `snap_slack` below the ridge's catch |
| 7 | `PortCutouts` | Subtracts PortCutters |
| 8 | `LidChamfer` | Native Chamfer on the lid's top face, which chamfers its whole outline: outer edge, port/SD notches and GPIO opening. The script finds the one face lying at `z_top` at build time ([lines 525–538](pi02w_case.py#L525-L538)) |
| 9 | `VentSlots` | One slot plus a linear pattern, centred on (`vent_x`, `vent_y`). Cut after the chamfer, so the slot edges stay sharp |

### Reference ([lines 548–594](pi02w_case.py#L548-L594))

- Plain `Part::Box` objects: the PCB (a box with its 4 holes cut out), the connectors, the SD card, the GPIO
  header housing, its pins and the solder joints under the board.
- Their positions are linked to Params through expressions, so they follow parameter changes.
- They're only used for the fit checks, never printed, and hidden in the saved file.

## 4. Checks ([lines 596–616](pi02w_case.py#L596-L616))

- Lists any object in an Invalid or Error state.
- Reports each part's validity, solid count, volume and bounding box.
- Checks that every sketch solves.
- Reports the intersection volume of each part with each reference object, and of base with lid. The only
  expected result is `Lid x PCB ≈ 8 mm³`, which is the intended clamp at the 4 posts.

The check output is only visible when the script runs under `freecadcmd`. In a GUI run, `print()` goes to the
Report view.

## 5. Display, save and export ([lines 618–646](pi02w_case.py#L618-L646))

- Hides everything, then shows Base, Lid and each one's Tip.
- When FreeCAD's interface is running (`App.GuiUp`), it sets 50 % transparency, which only the GUI can save.
- Saves the `.FCStd` and the STEP file. Only with `EXPORT_STL=1`, it also writes the STLs with `MeshPart`,
  rotating the lid copy 180° about X and dropping it onto the bed for printing.
- Finally calls `os._exit(0)`, but only in a headless GUI run, so it never closes a FreeCAD window you're working
  in.

Line numbers refer to the script as of 2026-10-10 and will drift as it changes.
