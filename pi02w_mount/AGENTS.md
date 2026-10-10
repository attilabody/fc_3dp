# Pi Zero 2 W case for 2020 extrusion

General 3D design conventions are in an `AGENTS.md` in one of the parent folders. Walk up from this folder and use the
nearest parent `AGENTS.md`. It is usually loaded automatically; if not, find and read it before working here.
If no parent has one (the folder moved outside the 3D tree), its last known location is
`/mnt/userdata_hdd/abody/Nextcloud/3D/AGENTS.md` (`~/Nextcloud` is a symlink to `/mnt/userdata_hdd/abody/Nextcloud`).
Tell the user that the link is broken.

- Source of truth: `pi02w_case.py`. It generates `pi02w_case.FCStd` and `pi02w_case.step`. STLs (lid flipped for
  top-down printing) only with `EXPORT_STL=1`.
- Rebuild: `QT_QPA_PLATFORM=offscreen freecad pi02w_case.py`. Use this command, not `freecadcmd`, so the 50 % transparency
  and visibility settings are saved. To see the check output (interference, validity), run `freecadcmd pi02w_case.py`
  first, then the GUI build.
- Coordinates: origin = PCB corner at the port edge / SD end; X along the 65 mm edge, Y towards the GPIO header,
  Z = 0 at the inner floor surface.
- Design:
  - The board sits on 4 standoffs with tapered locating pins.
  - Lid posts clamp the board (`clamp` interference) and receive the pin tips.
  - The snap fit is a base lip with ridges that catch in windows in the lid's outer wall.
  - The base flange extends at both ends for two M4 screws.
  - Lid has a vent array; the back wall has intake slots. No intakes on the CSI end (user: useless there).
- Status: first test print 2026-10-07.
  - Feedback 2026-10-08: the CSI connector overhangs the PCB edge by ~0.8 mm and was dangerously tight, so
    `gap_r` went from 0.5 to 1.5 and a `Conn_CSI` dummy was added.
  - Feedback 2026-10-08: the PCB is ~0.1-0.2 mm thicker than 1.4, and the lid didn't reach its position. So
    `board_t` went from 1.4 to 1.55 (estimate, not measured) and `snap_slack` became `=clamp - 0.05`, so the snap
    catches after 0.05 mm of squeeze instead of 0.10.
  - 2026-10-10: tolerances confirmed good enough on the first print, including `lip_gap` 0.15 (the sideways
    clearance between the base lip and the lid's outer wall, per side). The lid goes on easily, comes off after
    an initial extra pull (the snaps work), and doesn't wiggle when seated. Keep the lip/snap values as they are.
  - 2026-10-10: the mount holes moved to 10 mm from the GPIO-side outer edge (`mount_edge_off`), so that edge is
    flush with the beam face and the case overhangs on the port side. The right-end snap ridge and window use
    `case_cy` (the case centre).
  - 2026-10-10 (handling the print): lid chamfer extended to the whole top-face outline, including the HDMI/USB/SD
    notches and the GPIO opening. The user did it in the GUI; the script now matches. Vent slots stay sharp.

## Handover (state at end of session 2026-10-10)
- **Not yet test-printed:** all changes since the first print. These are `gap_r` 1.5, `board_t` 1.55, the
  `snap_slack` formula, the mount holes at 10 mm from the GPIO edge, and the full top-face chamfer. Next feedback
  should cover these: in particular whether the lid now snaps fully home (`board_t` and `snap_slack`). Ask for a
  caliper measurement of the PCB thickness if it hasn't been given yet.
- **Files on disk:**
  - `pi02w_case.step` is current: script output, verified Base 11162.8044 mm³ / Lid 4636.8932 mm³.
  - `pi02w_case.FCStd` on disk **predates the chamfer change**. The user's open FreeCAD session held the
    up-to-date (identical) version, unsaved. If the file on disk still has `LidChamfer` right after `LidBlock`
    (8-edge reference), it's stale: rebuild with the script.
  - `pi02w_case_base.stl` / `pi02w_case_lid.stl` are **stale** (pre-chamfer) leftovers. The user doesn't use STL;
    ask before deleting them.
- **Folder move:** the script, its outputs and the walkthrough use only paths relative to the script, so moving
  is safe. After the move, reopen the `.FCStd` from the new location in FreeCAD. `pi02w_case_walkthrough.md` line
  links may have drifted slightly after the latest edits.
- **Verification baselines** for a no-change rebuild: Base 11162.8044 mm³ (128 faces), Lid 4636.8932 mm³
  (132 faces, 342 edges), interference only `Lid x PCB` 8.086 mm³.
