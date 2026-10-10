# Raspberry Pi Zero 2 W case for 2020 aluminium extrusion (6 mm slot, M4 + T-nut)
#
# Generates a fully parametric FreeCAD document using a skeleton workflow:
#   Params (spreadsheet)  -> single source of truth for every dimension
#   Skeleton (body)       -> MasterSketch: board outline, mounting holes, header &
#                            port positions
#   Base / Lid bodies     -> reference the skeleton through SubShapeBinders
#   PortCutters body      -> port / SD openings, subtracted from Base and Lid
#   Reference group       -> dummy Pi Zero 2 W for fit checking (not printed)
#
# Mounting: two M4 screws through the base flange at the case ends into 6 mm slot T-nuts.
#
# Usage:  QT_QPA_PLATFORM=offscreen freecad pi02w_case.py   (headless GUI: also
#         stores display settings - visibility, 50 % transparency)
#     or  freecadcmd pi02w_case.py                          (geometry only)
# Output: pi02w_case.FCStd, pi02w_case.step
#         With EXPORT_STL=1 in the environment, also pi02w_case_base.stl and
#         pi02w_case_lid.stl (print orientation) for slicers that need meshes.
#
# Coordinates: origin = PCB corner at the port edge / SD end, X along the 65 mm
# board edge, Y towards the GPIO header, Z = 0 at the inner floor surface.

import math
import os
import re

import FreeCAD as App
import MeshPart
import Part
import Sketcher

V = App.Vector
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
NAME = "pi02w_case"

# ---------------------------------------------------------------------------
# Parameters: (alias, value or "=formula", comment). Formulas use alias names.
# ---------------------------------------------------------------------------
PARAMS = [
    ("# Board (official Zero 2 W mechanical drawing)",),
    ("board_L", 65.0, "PCB length"),
    ("board_W", 30.0, "PCB width"),
    ("board_t", 1.55, "PCB thickness - test print: 1.4 too thin, est. 1.5-1.6; measure"),
    ("hole_off", 3.5, "Mounting hole inset from PCB edges"),
    ("hole_dx", 58.0, "Mounting hole pitch X"),
    ("hole_dy", 23.0, "Mounting hole pitch Y"),
    ("hole_d", 2.75, "Mounting hole diameter"),
    ("hdmi_x", 12.4, "mini-HDMI centre X"),
    ("usb1_x", 41.4, "micro-USB (OTG/data) centre X"),
    ("usb2_x", 54.0, "micro-USB (power) centre X"),
    ("hdmi_zc", 1.6, "mini-HDMI centre height above PCB top"),
    ("usb_zc", 1.3, "micro-USB centre height above PCB top"),
    ("sd_y", 16.9, "microSD centre Y"),
    ("gpio_x", 32.5, "GPIO header centre X"),
    ("gpio_y", 26.5, "GPIO header centre Y"),
    ("# Shell",),
    ("wall", 2.4, "Side wall thickness"),
    ("floor_t", 2.0, "Floor thickness"),
    ("corner_r", 3.0, "Outer vertical corner radius"),
    ("gap_f", 1.5, "PCB edge to wall, port side (connectors overhang)"),
    ("gap_b", 0.5, "PCB edge to wall, GPIO side"),
    ("gap_l", 0.5, "PCB edge to wall, SD end"),
    ("gap_r", 1.5, "PCB edge to wall, CSI end (connector overhangs ~0.8)"),
    ("# Board support",),
    ("so_h", 3.5, "Standoff height (clears GPIO solder joints)"),
    ("so_d", 6.0, "Standoff diameter"),
    ("pin_d", 2.4, "Locating pin diameter"),
    ("pin_proj", 1.5, "Pin projection above PCB top"),
    ("pin_tip", 0.6, "Pin tip taper height"),
    ("pin_taper", 25.0, "Pin tip taper angle (deg)"),
    ("# Lid",),
    ("comp_clear", 4.0, "PCB top to lid ceiling (mini-HDMI ~3.3)"),
    ("lid_t", 2.0, "Lid plate thickness"),
    ("lid_chamfer", 0.8, "Chamfer on the lid top outer edge"),
    ("post_d", 5.0, "Clamp post diameter"),
    ("clamp", 0.15, "Clamp post interference on PCB (tune!)"),
    ("post_hole_clr", 0.4, "Pin receiving hole: diameter clearance"),
    ("gpio_open_L", 52.0, "GPIO opening length"),
    ("gpio_open_W", 7.0, "GPIO opening width"),
    ("vent_n", 9, "Number of vent slots"),
    ("vent_w", 2.0, "Vent slot width"),
    ("vent_len", 14.0, "Vent slot length (across the board)"),
    ("vent_pitch", 4.0, "Vent slot pitch"),
    ("vent_x", 32.5, "Vent array centre X (over the SoC)"),
    ("vent_y", 12.5, "Vent array centre Y"),
    ("intake_w", 3.0, "Intake slot width (base walls)"),
    ("intake_h", 2.0, "Intake slot height (keep intake_z + intake_h < z_r)"),
    ("intake_z", 0.5, "Intake slot bottom Z"),
    ("intake_pitch", 5.0, "Intake slot pitch"),
    ("intake_n_back", 10, "Intake slots in the back (GPIO side) wall"),
    ("# Snap fit",),
    ("z_r", 3.0, "Shoulder height: full wall below, lip above"),
    ("lip_t", 1.2, "Base lip thickness"),
    ("lip_gap", 0.15, "Lip to lid skirt clearance"),
    ("lip_top_gap", 0.2, "Lip top to lid ceiling gap"),
    ("skirt_gap", 0.2, "Lid skirt bottom to shoulder gap"),
    ("ridge_p", 0.5, "Snap ridge protrusion"),
    ("ridge_h", 1.5, "Snap ridge height"),
    ("ridge_len", 8.0, "Snap ridge length"),
    ("ridge_z", 5.0, "Snap ridge bottom Z"),
    ("snap_slack", "=clamp - 0.05", "Window bottom below ridge bottom (snap catches after 0.05 squeeze)"),
    ("win_clr", 0.3, "Snap window clearance beyond the ridge (ends and top)"),
    ("ridge_b1_x", 16.0, "Back ridge 1 X"),
    ("ridge_b2_x", 49.0, "Back ridge 2 X"),
    ("ridge_f_x", 28.4, "Front ridge X (between HDMI and USB)"),
    ("# Port cutouts (sized for plug overmoulds)",),
    ("hdmi_w", 16.0, "mini-HDMI cutout width"),
    ("hdmi_h", 9.0, "mini-HDMI cutout height (opens to top)"),
    ("usb_w", 11.0, "micro-USB cutout width (both ports, merged)"),
    ("usb_h", 7.0, "micro-USB cutout height (opens to top)"),
    ("sd_cut_w", 14.0, "SD access notch width"),
    ("sd_cut_z", 3.0, "SD notch bottom Z"),
    ("sd_cut_in", 2.0, "SD notch reach over PCB (lid finger access)"),
    ("# 2020 mount (6 mm slot, M4 + T-nut)",),
    ("m4_d", 4.4, "M4 clearance hole"),
    ("flange_L", 11.0, "Base flange extension beyond each end wall"),
    ("flange_t", 4.0, "Base flange thickness (must stay below z_r + floor_t)"),
    ("mount_edge_off", 10.0, "Screw centre to GPIO-side outer edge (2020: edge flush with beam)"),
    ("flange_hole_off", 5.5, "End wall to screw centre (M4 head dia 7)"),
    ("# Derived (do not edit)",),
    ("z_bt", "=so_h + board_t", "PCB top Z"),
    ("z_ceil", "=z_bt + comp_clear", "Lid ceiling Z"),
    ("z_top", "=z_ceil + lid_t", "Lid top Z"),
    ("z_split", "=z_ceil - lip_top_gap", "Lip top Z"),
    ("x_in0", "=-gap_l", "Cavity X min"),
    ("x_in1", "=board_L + gap_r", "Cavity X max"),
    ("y_in0", "=-gap_f", "Cavity Y min"),
    ("y_in1", "=board_W + gap_b", "Cavity Y max"),
    ("x_out0", "=x_in0 - wall", "Outer X min"),
    ("x_out1", "=x_in1 + wall", "Outer X max"),
    ("y_out0", "=y_in0 - wall", "Outer Y min"),
    ("y_out1", "=y_in1 + wall", "Outer Y max"),
    ("lip_r", "=corner_r - wall + lip_t", "Lip outer corner radius"),
    ("skirt_off", "=lip_t + lip_gap", "Cavity face to skirt inner face"),
    ("skirt_r", "=lip_r + lip_gap", "Skirt inner corner radius"),
    ("skirt_t", "=wall - skirt_off", "Lid skirt thickness"),
    ("case_cy", "=(y_out0 + y_out1) / 2", "Case centre Y"),
    ("mount_y", "=y_out1 - mount_edge_off", "Mount screw Y"),
    ("mount_x0", "=x_out0 - flange_hole_off", "Mount screw 1 X (SD end)"),
    ("mount_x1", "=x_out1 + flange_hole_off", "Mount screw 2 X"),
]

P = {}  # numeric values, mirrored from the spreadsheet
for row in PARAMS:
    if len(row) == 3:
        name, val, _ = row
        P[name] = eval(val[1:], {}, dict(P)) if isinstance(val, str) else float(val)

_ident = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


def ex(expr):
    """Python-style param expression -> FreeCAD expression on the Params sheet."""
    expr = str(expr)
    return _ident.sub(lambda m: "Params." + m.group(1) if m.group(1) in P else m.group(1), expr)


def nv(expr):
    """Numeric value of a param expression."""
    return float(eval(str(expr), {}, dict(P)))


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------
doc = App.newDocument(NAME)


def make_sheet():
    sh = doc.addObject("Spreadsheet::Sheet", "Params")
    r = 1
    for row in PARAMS:
        if len(row) == 1:
            sh.set(f"A{r}", row[0][2:])
            sh.setStyle(f"A{r}", "bold")
        else:
            name, val, comment = row
            sh.set(f"A{r}", name)
            sh.set(f"B{r}", str(val))
            sh.setAlias(f"B{r}", name)
            sh.set(f"C{r}", comment)
        r += 1
    sh.setColumnWidth("A", 130)
    sh.setColumnWidth("C", 330)
    return sh


def plane(body, role):
    return [o for o in body.Origin.OriginFeatures if o.Role == role][0]


def sketch(body, name, role="XY_Plane", offset="0"):
    """Sketch on a body origin plane, offset along its normal by a param expression."""
    sk = body.newObject("Sketcher::SketchObject", name)
    sk.AttachmentSupport = [(plane(body, role), "")]
    sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(V(0, 0, nv(offset)), App.Rotation())
    if str(offset) != "0":
        sk.setExpression(".AttachmentOffset.Base.z", ex(offset))
    return sk


def cname(sk, idx, name, expr):
    sk.renameConstraint(idx, name)
    sk.setExpression(f".Constraints.{name}", ex(expr))


def fix_point(sk, geo, pos, ue, ve, tag):
    c = sk.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, geo, pos, nv(ue)))
    cname(sk, c, f"{tag}_u", ue)
    c = sk.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, geo, pos, nv(ve)))
    cname(sk, c, f"{tag}_v", ve)


def polygon(sk, pts, tag):
    """Closed polygon, each vertex driven by (u_expr, v_expr)."""
    n = len(pts)
    first = sk.GeometryCount
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        sk.addGeometry(Part.LineSegment(V(nv(a[0]), nv(a[1]), 0), V(nv(b[0]), nv(b[1]), 0)))
    for i in range(n):
        sk.addConstraint(Sketcher.Constraint("Coincident", first + i, 2, first + (i + 1) % n, 1))
    for i in range(n):
        fix_point(sk, first + i, 1, pts[i][0], pts[i][1], f"{tag}_p{i}")


def rect(sk, x0, y0, x1, y1, tag):
    polygon(sk, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], tag)


def rounded_rect(sk, x0, y0, x1, y1, r, tag):
    """Rounded rectangle: corner centres and radius driven by expressions."""
    X0, Y0, X1, Y1, R = (nv(e) for e in (x0, y0, x1, y1, r))
    # corner centres (expr, numeric) BL, BR, TR, TL
    cx = [(f"({x0}) + ({r})", X0 + R), (f"({x1}) - ({r})", X1 - R)]
    cy = [(f"({y0}) + ({r})", Y0 + R), (f"({y1}) - ({r})", Y1 - R)]
    corners = [(cx[0], cy[0], math.pi, 1.5 * math.pi),
               (cx[1], cy[0], 1.5 * math.pi, 2 * math.pi),
               (cx[1], cy[1], 0.0, 0.5 * math.pi),
               (cx[0], cy[1], 0.5 * math.pi, math.pi)]
    g = sk.GeometryCount
    arcs, lines = [], []
    for (ux, uy, a0, a1) in corners:
        arcs.append(sk.addGeometry(Part.ArcOfCircle(
            Part.Circle(V(ux[1], uy[1], 0), V(0, 0, 1), R), a0, a1)))
    segs = [((X0 + R, Y0), (X1 - R, Y0)), ((X1, Y0 + R), (X1, Y1 - R)),
            ((X1 - R, Y1), (X0 + R, Y1)), ((X0, Y1 - R), (X0, Y0 + R))]
    for (a, b) in segs:
        lines.append(sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0))))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Tangent", arcs[i], 2, lines[i], 1))
        sk.addConstraint(Sketcher.Constraint("Tangent", lines[i], 2, arcs[(i + 1) % 4], 1))
    for i, (ux, uy, _, _) in enumerate(corners):
        fix_point(sk, arcs[i], 3, ux[0], uy[0], f"{tag}_c{i}")
        c = sk.addConstraint(Sketcher.Constraint("Radius", arcs[i], R))
        cname(sk, c, f"{tag}_r{i}", r)


def circle_at(sk, ue, ve, d, tag):
    g = sk.addGeometry(Part.Circle(V(nv(ue), nv(ve), 0), V(0, 0, 1), nv(d) / 2))
    fix_point(sk, g, 3, ue, ve, tag)
    c = sk.addConstraint(Sketcher.Constraint("Diameter", g, nv(d)))
    cname(sk, c, f"{tag}_d", d)


def circles_on_holes(sk, binder, d, tag):
    """Circles concentric with the skeleton's mounting holes (via binder)."""
    for i, edge in enumerate(hole_edges(binder)):
        sk.addExternal(binder.Name, edge)
        ext = -3 - i
        c0 = binder.Shape.getElement(edge).Curve.Center
        g = sk.addGeometry(Part.Circle(V(c0.x, c0.y, 0), V(0, 0, 1), nv(d) / 2))
        sk.addConstraint(Sketcher.Constraint("Coincident", g, 3, ext, 3))
        c = sk.addConstraint(Sketcher.Constraint("Diameter", g, nv(d)))
        cname(sk, c, f"{tag}{i}_d", d)


def hole_edges(binder):
    """Binder edge names of the 4 mounting-hole circles (diameter hole_d)."""
    names = []
    for i, e in enumerate(binder.Shape.Edges):
        if isinstance(e.Curve, Part.Circle) and abs(e.Curve.Radius * 2 - P["hole_d"]) < 1e-6:
            names.append(f"Edge{i + 1}")
    assert len(names) == 4, names
    return names


def pad(body, name, sk, length, reversed_=False, taper=None):
    f = body.newObject("PartDesign::Pad", name)
    f.Profile = sk
    f.Length = nv(length)
    f.setExpression("Length", ex(length))
    f.Reversed = reversed_
    if taper is not None:
        f.TaperAngle = nv(taper)
        f.setExpression("TaperAngle", ex(taper))
    sk.Visibility = False
    return f


def pad_mid(body, name, sk, length):
    f = pad(body, name, sk, length)
    f.SideType = "Symmetric"
    return f


def pocket(body, name, sk, length=None, reversed_=False, midplane=False):
    f = body.newObject("PartDesign::Pocket", name)
    f.Profile = sk
    if length is None:
        f.Type = "ThroughAll"
    else:
        f.Length = nv(length)
        f.setExpression("Length", ex(length))
    f.Reversed = reversed_
    if midplane:
        f.SideType = "Symmetric"
    sk.Visibility = False
    return f


def axis(body, role):
    return [o for o in body.Origin.OriginFeatures if o.Role == role][0]


def linear_pattern(body, name, feature, axis_role, n, pitch):
    """Linear pattern of one feature; n and pitch are param expressions."""
    f = body.newObject("PartDesign::LinearPattern", name)
    f.Originals = [feature]
    f.Direction = (axis(body, axis_role), [""])
    f.Length = nv(f"({n} - 1) * {pitch}")
    f.setExpression("Length", ex(f"({n} - 1) * {pitch}"))
    f.Occurrences = int(nv(n))
    f.setExpression("Occurrences", ex(n))
    feature.Visibility = False
    body.Tip = f  # a newly created pattern is not made the tip automatically
    return f


def binder(body, name, src):
    b = body.newObject("PartDesign::SubShapeBinder", name)
    b.Support = [(src, ("",))]
    b.Visibility = False
    return b


def box(body, name, x, y, z, L, W, H):
    """Additive box with all dimensions/positions bound to expressions."""
    f = body.newObject("PartDesign::AdditiveBox", name)
    f.AttachmentSupport = [(plane(body, "XY_Plane"), "")]
    f.MapMode = "FlatFace"
    for prop, e in (("Length", L), ("Width", W), ("Height", H)):
        setattr(f, prop, nv(e))
        f.setExpression(prop, ex(e))
    f.AttachmentOffset = App.Placement(V(nv(x), nv(y), nv(z)), App.Rotation())
    for ax, e in (("x", x), ("y", y), ("z", z)):
        f.setExpression(f".AttachmentOffset.Base.{ax}", ex(e))
    return f


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
sheet = make_sheet()
doc.recompute()

# --- Skeleton ---------------------------------------------------------------
skel_body = doc.addObject("PartDesign::Body", "Skeleton")
skel = sketch(skel_body, "MasterSketch")
rect(skel, "0", "0", "board_L", "board_W", "pcb")
for i, (hx, hy) in enumerate([("hole_off", "hole_off"),
                              ("hole_off + hole_dx", "hole_off"),
                              ("hole_off + hole_dx", "hole_off + hole_dy"),
                              ("hole_off", "hole_off + hole_dy")]):
    circle_at(skel, hx, hy, "hole_d", f"hole{i}")
rect(skel, "gpio_x - 25.4", "gpio_y - 2.54", "gpio_x + 25.4", "gpio_y + 2.54", "hdr")
# port / SD centre markers (short ticks across the board edge)
for tag, xe in (("hdmi", "hdmi_x"), ("usb1", "usb1_x"), ("usb2", "usb2_x")):
    g = skel.addGeometry(Part.LineSegment(V(nv(xe), -1, 0), V(nv(xe), 1, 0)))
    fix_point(skel, g, 1, xe, "-1", f"{tag}_a")
    fix_point(skel, g, 2, xe, "1", f"{tag}_b")
g = skel.addGeometry(Part.LineSegment(V(-1, nv("sd_y"), 0), V(1, nv("sd_y"), 0)))
fix_point(skel, g, 1, "-1", "sd_y", "sd_a")
fix_point(skel, g, 2, "1", "sd_y", "sd_b")
doc.recompute()

# --- Port cutters (shared by base and lid) ----------------------------------
cut = doc.addObject("PartDesign::Body", "PortCutters")
box(cut, "HDMI_cut", "hdmi_x - hdmi_w / 2", "y_out0 - 1", "z_bt + hdmi_zc - hdmi_h / 2",
    "hdmi_w", "1 - y_out0", "z_top + 1 - (z_bt + hdmi_zc - hdmi_h / 2)")
box(cut, "USB_cut", "usb1_x - usb_w / 2", "y_out0 - 1", "z_bt + usb_zc - usb_h / 2",
    "usb2_x - usb1_x + usb_w", "1 - y_out0", "z_top + 1 - (z_bt + usb_zc - usb_h / 2)")
box(cut, "SD_cut", "x_out0 - 1", "sd_y - sd_cut_w / 2", "sd_cut_z",
    "sd_cut_in + 1 - x_out0", "sd_cut_w", "z_top + 1 - sd_cut_z")
cut.Visibility = False
doc.recompute()



def port_cut(body):
    """Subtract the shared PortCutters body through a dedicated binder (an object
    can only belong to one Boolean group, so each body gets its own binder)."""
    b = doc.addObject("PartDesign::SubShapeBinder", f"PortCutters_{body.Name}")
    b.Support = [(cut, ("",))]
    b.Visibility = False
    f = body.newObject("PartDesign::Boolean", "PortCutouts")
    f.Type = "Cut"
    f.addObject(b)
    return f


# --- Base ---------------------------------------------------------------------
base = doc.addObject("PartDesign::Body", "Base")
bsk = binder(base, "SkeletonBinder", skel)
doc.recompute()

s = sketch(base, "ShellSketch", offset="-floor_t")
rounded_rect(s, "x_out0", "y_out0", "x_out1", "y_out1", "corner_r", "out")
pad(base, "Shell", s, "floor_t + z_r")

# full-width base flange, extended at both ends to carry the mounting screws
s = sketch(base, "FlangeSketch", offset="-floor_t")
rounded_rect(s, "x_out0 - flange_L", "y_out0", "x_out1 + flange_L", "y_out1", "corner_r", "fl")
pad(base, "Flange", s, "flange_t")

s = sketch(base, "LipSketch", offset="z_r")
rounded_rect(s, "x_in0 - lip_t", "y_in0 - lip_t", "x_in1 + lip_t", "y_in1 + lip_t", "lip_r", "lip")
pad(base, "Lip", s, "z_split - z_r")

s = sketch(base, "CavitySketch")
rect(s, "x_in0", "y_in0", "x_in1", "y_in1", "cav")
pocket(base, "Cavity", s, reversed_=True)

s = sketch(base, "StandoffSketch")
circles_on_holes(s, bsk, "so_d", "so")
pad(base, "Standoffs", s, "so_h")

s = sketch(base, "PinSketch", offset="so_h")
circles_on_holes(s, bsk, "pin_d", "pin")
pad(base, "Pins", s, "board_t + pin_proj - pin_tip")

s = sketch(base, "PinTipSketch", offset="z_bt + pin_proj - pin_tip")
circles_on_holes(s, bsk, "pin_d", "tip")
pad(base, "PinTips", s, "pin_tip", taper="-pin_taper")

# snap ridges: triangular-ish profile, ramp on top (lid slides down over it)
def ridge_profile(n0, sgn):
    """(n, z) profile; n0 = lip outer face coordinate, sgn = outward direction."""
    return [(f"{n0} - ({sgn}) * 0.3", "ridge_z"),
            (f"{n0} + ({sgn}) * ridge_p", "ridge_z + 0.3"),
            (f"{n0} + ({sgn}) * ridge_p", "ridge_z + 0.6"),
            (f"{n0} - ({sgn}) * 0.3", "ridge_z + ridge_h")]


for tag, xe in (("RidgeBack1", "ridge_b1_x"), ("RidgeBack2", "ridge_b2_x")):
    s = sketch(base, tag + "Sketch", role="YZ_Plane", offset=xe)
    polygon(s, ridge_profile("(y_in1 + lip_t)", "1"), tag)
    pad_mid(base, tag, s, "ridge_len")
s = sketch(base, "RidgeFrontSketch", role="YZ_Plane", offset="ridge_f_x")
polygon(s, ridge_profile("(y_in0 - lip_t)", "-1"), "RidgeFront")
pad_mid(base, "RidgeFront", s, "ridge_len")
# right end: XZ plane, u = +X, normal = -Y  -> offset = -case_cy
s = sketch(base, "RidgeRightSketch", role="XZ_Plane", offset="-case_cy")
polygon(s, ridge_profile("(x_in1 + lip_t)", "1"), "RidgeRight")
pad_mid(base, "RidgeRight", s, "ridge_len")

s = sketch(base, "MountHoleSketch", offset="flange_t - floor_t")
circle_at(s, "mount_x0", "mount_y", "m4_d", "mh0")
circle_at(s, "mount_x1", "mount_y", "m4_d", "mh1")
pocket(base, "MountHoles", s)

port_cut(base)

# air intakes: slots in the bottom band of the back wall (below the
# lid skirt); air enters under the board and leaves through the lid vents
s = sketch(base, "IntakeBackSketch", role="XZ_Plane", offset="-(y_in1 + wall / 2)")
IX0 = "board_L / 2 - (intake_n_back - 1) * intake_pitch / 2"
rect(s, f"{IX0} - intake_w / 2", "intake_z", f"{IX0} + intake_w / 2", "intake_z + intake_h",
     "intakeB")
f = pocket(base, "IntakeBack", s, "wall + 1", midplane=True)
linear_pattern(base, "IntakesBack", f, "X_Axis", "intake_n_back", "intake_pitch")
doc.recompute()

# --- Lid ----------------------------------------------------------------------
lid = doc.addObject("PartDesign::Body", "Lid")
lsk = binder(lid, "SkeletonBinder", skel)
doc.recompute()

s = sketch(lid, "LidOuterSketch", offset="z_r + skirt_gap")
rounded_rect(s, "x_out0", "y_out0", "x_out1", "y_out1", "corner_r", "out")
pad(lid, "LidBlock", s, "z_top - z_r - skirt_gap")

s = sketch(lid, "LidInnerSketch", offset="z_ceil")
rounded_rect(s, "x_in0 - skirt_off", "y_in0 - skirt_off", "x_in1 + skirt_off",
             "y_in1 + skirt_off", "skirt_r", "in")
pocket(lid, "LidHollow", s)

s = sketch(lid, "PostSketch", offset="z_ceil")
circles_on_holes(s, lsk, "post_d", "post")
pad(lid, "ClampPosts", s, "z_ceil - z_bt + clamp", reversed_=True)

s = sketch(lid, "PostHoleSketch", offset="z_bt - clamp")
circles_on_holes(s, lsk, "pin_d + post_hole_clr", "ph")
pocket(lid, "PinReceivers", s, "pin_proj + clamp + 0.4", reversed_=True)

s = sketch(lid, "GpioSketch", offset="z_top")
rect(s, "gpio_x - gpio_open_L / 2", "gpio_y - gpio_open_W / 2",
     "gpio_x + gpio_open_L / 2", "gpio_y + gpio_open_W / 2", "gpio")
pocket(lid, "GpioOpening", s)


# snap windows through the skirt, matching the ridges
WIN_Z0 = "ridge_z - snap_slack"
WIN_Z1 = "ridge_z + ridge_h + win_clr"
for tag, xe in (("WinBack1", "ridge_b1_x"), ("WinBack2", "ridge_b2_x"), ("WinFront", "ridge_f_x")):
    s = sketch(lid, tag + "Sketch", role="XZ_Plane", offset="-(y_in1 + skirt_off + skirt_t / 2)"
               if "Back" in tag else "-(y_in0 - skirt_off - skirt_t / 2)")
    rect(s, f"{xe} - ridge_len / 2 - win_clr", WIN_Z0, f"{xe} + ridge_len / 2 + win_clr", WIN_Z1, tag)
    pocket(lid, tag, s, "skirt_t + 1", midplane=True)
s = sketch(lid, "WinRightSketch", role="YZ_Plane", offset="x_in1 + skirt_off + skirt_t / 2")
rect(s, "case_cy - ridge_len / 2 - win_clr", WIN_Z0, "case_cy + ridge_len / 2 + win_clr", WIN_Z1,
     "WinRight")
pocket(lid, "WinRight", s, "skirt_t + 1", midplane=True)

lid_cut = port_cut(lid)
doc.recompute()

# chamfer the whole top-face outline (outer edge, port/SD notches, GPIO opening) after
# the cuts; the vent slots come later and stay sharp. A face reference on a Boolean
# result was stress-tested on FreeCAD 1.1 and stays on the top face.
top = [i for i, fc in enumerate(lid_cut.Shape.Faces)
       if abs(fc.BoundBox.ZMin - nv("z_top")) < 1e-6 and abs(fc.BoundBox.ZMax - nv("z_top")) < 1e-6]
assert len(top) == 1, top
f = lid.newObject("PartDesign::Chamfer", "LidChamfer")
f.Base = (lid_cut, [f"Face{top[0] + 1}"])
f.Size = nv("lid_chamfer")
f.setExpression("Size", ex("lid_chamfer"))

# ventilation: one slot + linear pattern, centred on (vent_x, vent_y)
s = sketch(lid, "VentSketch", offset="z_top")
VX0 = "vent_x - (vent_n - 1) * vent_pitch / 2"
rect(s, f"{VX0} - vent_w / 2", "vent_y - vent_len / 2",
     f"{VX0} + vent_w / 2", "vent_y + vent_len / 2", "vent")
vent = pocket(lid, "VentSlot", s, "lid_t + 1")
linear_pattern(lid, "VentSlots", vent, "X_Axis", "vent_n", "vent_pitch")
doc.recompute()

# --- Reference Pi Zero 2 W (fit check only) -----------------------------------
ref = doc.addObject("App::DocumentObjectGroup", "Reference")


def ref_box(name, x, y, z, L, W, H, color):
    b = doc.addObject("Part::Box", name)
    for prop, e in (("Length", L), ("Width", W), ("Height", H)):
        b.setExpression(prop, ex(e))
    for ax, e in (("x", x), ("y", y), ("z", z)):
        b.setExpression(f".Placement.Base.{ax}", ex(e))
    ref.addObject(b)
    if hasattr(b, "ViewObject") and b.ViewObject:
        b.ViewObject.ShapeColor = color
    return b


pcb = ref_box("PCB_blank", "0", "0", "so_h", "board_L", "board_W", "board_t", (0.1, 0.5, 0.1))
holes = []
for i, (hx, hy) in enumerate([("hole_off", "hole_off"), ("hole_off + hole_dx", "hole_off"),
                              ("hole_off + hole_dx", "hole_off + hole_dy"),
                              ("hole_off", "hole_off + hole_dy")]):
    c = doc.addObject("Part::Cylinder", f"PCB_hole{i}")
    c.setExpression("Radius", ex("hole_d / 2"))
    c.setExpression("Height", ex("board_t + 2"))
    c.setExpression(".Placement.Base.x", ex(hx))
    c.setExpression(".Placement.Base.y", ex(hy))
    c.setExpression(".Placement.Base.z", ex("so_h - 1"))
    holes.append(c)
hu = doc.addObject("Part::MultiFuse", "PCB_holes")
hu.Shapes = holes
pcb_cut = doc.addObject("Part::Cut", "PCB")
pcb_cut.Base, pcb_cut.Tool = pcb, hu
ref.addObject(pcb_cut)
# connector envelopes (approximate)
ref_box("Conn_HDMI", "hdmi_x - 5.6", "-0.5", "z_bt", "11.2", "7.5", "3.3", (0.7, 0.7, 0.7))
ref_box("Conn_USB1", "usb1_x - 4", "-1.2", "z_bt", "8", "5.6", "2.7", (0.7, 0.7, 0.7))
ref_box("Conn_USB2", "usb2_x - 4", "-1.2", "z_bt", "8", "5.6", "2.7", (0.7, 0.7, 0.7))
ref_box("Conn_CSI", "board_L - 3.5", "6.9", "z_bt", "4.3", "16", "1.2", (0.7, 0.7, 0.7))
ref_box("Conn_SD", "1.5", "sd_y - 6", "z_bt", "11.5", "12", "1.4", (0.7, 0.7, 0.7))
ref_box("SD_card", "-2.5", "sd_y - 5.5", "z_bt + 0.3", "15", "11", "0.8", (0.2, 0.2, 0.8))
ref_box("GPIO_housing", "gpio_x - 25.4", "gpio_y - 2.54", "z_bt", "50.8", "5.08", "2.5",
        (0.1, 0.1, 0.1))
ref_box("GPIO_pins", "gpio_x - 24.8", "gpio_y - 1.6", "z_bt + 2.5", "49.6", "3.2", "6",
        (0.8, 0.7, 0.2))
ref_box("GPIO_solder", "gpio_x - 24.8", "gpio_y - 1.6", "so_h - 2.5", "49.6", "3.2", "2.5",
        (0.8, 0.7, 0.2))
doc.recompute()

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
print("Invalid objects:", bad)
for b in (base, lid):
    print(f"{b.Name}: valid={b.Shape.isValid()} solids={len(b.Shape.Solids)} "
          f"vol={b.Shape.Volume:.0f} bbox={b.Shape.BoundBox}")
for o in doc.Objects:
    if o.TypeId == "Sketcher::SketchObject":
        dof = o.solve()
        if dof != 0:
            print("Sketch solve problem:", o.Name, dof)

ref_shapes = [o for o in ref.Group if o.Name != "PCB_blank"]
for b in (base, lid):
    for r in ref_shapes:
        common = b.Shape.common(r.Shape).Volume
        if common > 1e-3:
            print(f"Interference {b.Name} x {r.Name}: {common:.3f} mm3")
print("Base x Lid overlap:", round(base.Shape.common(lid.Shape).Volume, 3))

def stl(shape, path):
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.01, AngularDeflection=0.1).write(path)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
# Display: only Base and Lid (with their tips) shown
for o in doc.Objects:
    o.Visibility = False
for o in (base, base.Tip, lid, lid.Tip):
    o.Visibility = True
if App.GuiUp:
    for b in (base, lid):
        b.ViewObject.Transparency = 50
else:
    print("Note: run via the headless GUI (see Usage) to store 50 % transparency")

doc.saveAs(os.path.join(OUT_DIR, NAME + ".FCStd"))
Part.export([base, lid], os.path.join(OUT_DIR, NAME + ".step"))
if os.environ.get("EXPORT_STL") == "1":
    stl(base.Shape, os.path.join(OUT_DIR, NAME + "_base.stl"))
    lid_print = lid.Shape.copy()
    lid_print.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    lid_print.translate(V(0, 0, -lid_print.BoundBox.ZMin))
    stl(lid_print, os.path.join(OUT_DIR, NAME + "_lid.stl"))
print("Done")

if App.GuiUp and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    os._exit(0)  # headless batch run: quit the GUI instance
