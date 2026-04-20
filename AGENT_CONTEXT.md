# AGENT_CONTEXT

Updated: `2026-04-20`  
Project root: `C:\Users\User\Desktop\Antigravity\space_rpg_ursina`  
Main runtime file: `space_rpg_prototype.py`

## 1) Project snapshot

- Stack: `Python + Ursina (Panda3D)`.
- Prototype: first-person sci-fi scene with NPC, dialogues, pause menu, HUD, galaxy/sector map.
- User focus right now is not gameplay features, but UI architecture stability across window modes and resolutions.

## 2) What the user explicitly wants now

The user requested a system-level UI redesign (not cosmetic tweaks):

- Single, predictable UI scaling system for all screens.
- Reference resolution design grid (`1920x1080`).
- One shared UI scale manager with uniform scale (`min(scale_x, scale_y)` style behavior).
- No mixed ad-hoc scaling for panels/text/icons.
- Stable anchors/safe area layout (instead of random absolute placements).
- Same style/mechanics for HUD, Pause, Dialogue, Galaxy Map, Sector Map, and crosshair.
- Fix window-mode behavior (windowed/borderless/fullscreen), including centering/alignment issues outside fullscreen.

## 3) Reported UI symptoms (confirmed by user screenshots)

- UI sometimes appears effectively “+200%”.
- After partial fixes, some views become too tiny and misaligned.
- Menus/text can overflow screen bounds.
- Map overlays and side panels look offset and inconsistent.
- Non-fullscreen modes can position content/window incorrectly.

## 4) Technical state found in codebase

In `space_rpg_prototype.py` the code already contains parts of scaling infrastructure:

- `make_ui_root(...)`
- `normalize_ui_camera(...)`
- `apply_ui_scale()`
- Dedicated UI sections for `PauseMenu`, `DialogueUI`, `GalaxyMapUI`, HUD/crosshair roots.

But the current behavior is still unstable because layout/scaling logic is fragmented:

- many local hard-coded positions/sizes,
- mixed assumptions between different UI blocks,
- partial per-screen overrides that break visual consistency.

## 5) Asset sourcing research done (GitHub)

User asked to research GitHub packs.  
License policy chosen for adoption shortlist: `MIT / CC0 / CC-BY`.

Vetted candidates:

- `devdogio/sci-fi-ui` (MIT) — primary sci-fi UI pack candidate.
- `game-icons/icons` (CC-BY) — large icon base for statuses/markers/actions.
- `iwenzhou/kenney` (CC0-1.0) — Kenney mirror/fallback asset base.
- `DevsDaddy/OneUIKit` (MIT) — optional component baseline.

Conditional (license not in selected policy):

- `arashtad/Sci-Fi-Games-UI-Elements-Pack` (GPLv3)
- `jinincarnate/off-screen-indicator` (GPL-3.0)

## 6) Git/repository facts relevant to handoff

Top-level repo: `C:\Users\User\Desktop\Antigravity`  
Branch: `main`  
Remote: `origin -> https://github.com/Lemozya/Antigravity1.git`

Important: inside `space_rpg_ursina` there are embedded git repos:

- `assets/external/Starter-Kit-FPS/.git` (origin: `KenneyNL/Starter-Kit-FPS`, HEAD `185fd23`)
- `assets/external/ursina_repo/.git` (origin: `pokepetter/ursina`, HEAD `60f9254`)

If added from superproject without cleanup, these paths are tracked as gitlinks (embedded repos/submodule-like entries), not full file snapshots.

## 7) Current acceptance targets for UI fix

Must validate UI on at least:

- `1280x720`
- `1600x900`
- `1920x1080`
- `2560x1440`
- ultrawide (if supported)

Pass criteria:

- readable UI everywhere,
- no giant/microscopic oscillation,
- stable hierarchy of title/subtitle/body/meta text,
- click hitboxes aligned to visuals,
- consistent layout in HUD/pause/dialogue/maps/crosshair,
- no control regressions in `Esc`/`Enter` flows.

## 8) Immediate working priority

1. Stabilize window mode + centering behavior.
2. Unify all UI through one scale/layout pipeline.
3. Normalize typography and panel bounds with clamped theme constants.
4. Apply asset-driven visual system consistently to galaxy/sector UI and shared HUD components.
