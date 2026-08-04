# Stitch prompt — VOXD GUI / UI-UX

Paste the prompt below into [Stitch](https://stitch.withgoogle.com/) (or a
similar AI UI generator) to produce VOXD's desktop UI for Windows, Linux, and
macOS. It is written to be self-contained: product, surfaces, states, platform
nuances, the liquid-glass aesthetic, and a dead-simple get-started flow.

---

## Prompt

Design the complete desktop UI/UX for **VOXD**, a local-first AI voice
dictation app. The user holds a hotkey, speaks, and VOXD transcribes their
words locally with Whisper and types the result into whatever app is focused.
No audio leaves the machine. The app runs as a **system-tray resident**
application with a small set of on-demand windows.

Produce high-fidelity designs for **three platforms side by side**, each
respecting its native chrome and conventions:

1. **Windows 11 / 10** — Mica/acrylic backdrop, Fluent style, rounded 8px
   corners, Segoe UI variable.
2. **Linux (GNOME on Wayland)** — libadwaita / GTK4 aesthetic, Inter, flat
   surfaces, rounded 12px.
3. **macOS 26 (Tahoe)** — **Liquid Glass** as the hero material: translucent,
   refractive, edge-highlighted glass that blurs and tint-shifts over the
   content behind it, with real-time dynamic blur and specular rim light.
   Sidebar and floating panels are Liquid Glass. Use SF Pro, rounded 11px,
   vibrancy.

Across all three: a cohesive **"liquid glass" design language** — translucent
frosted surfaces, subtle refraction, depth via layered blur, soft specular
highlights on edges, gentle spring-based motion (200–320ms, ease-out). Light
and dark mode for every screen. High contrast / reduced-motion variants.
Accessibility: keyboard-navigable, focus rings, ARIA labels, minimum 44px tap
targets, 4.5:1 contrast.

### Product surfaces to design

1. **First-run onboarding / "Get Started" wizard** (the hero flow — make it
   feel effortless, 3 steps max, always show progress):
   - Step 1 **Welcome** — one sentence: "Hold a key, speak, VOXD types it."
     Single primary button: "Get started." A small "Local & private — your
     audio never leaves this computer" reassurance line with a lock glyph.
   - Step 2 **Engine + model setup** — VOXD downloads a prebuilt Whisper
     engine and a small model. Show a single combined progress view: a
     progress ring/bar with percentage, the current step label ("Downloading
     Whisper engine… 4.1 MB", "Downloading model — base.en… 75 MB",
     "Verifying…"), and an estimated time. No jargon, no command line. A
     "Skip for now (set up later)" tertiary link. On error: friendly card with
     "Retry" and "What happened?" expandable.
   - Step 3 **Hotkey + mic test** — let the user pick/record the global hotkey
     (default F8), choose the microphone from a list with live VU meter, and
     do a 3-second test dictation that types into a built-in preview field so
     they *see* it working. Primary button: "Start using VOXD."
2. **System tray icon + menu** — the primary persistent surface. Tray icon
   reflects state with both color and glyph (never color alone):
   🎤 Ready · 🔴 Listening · 🧠 Transcribing · ⌨️ Writing · ⚠ Error. Tray menu
   items: Start/Stop recording (single left-click also toggles), ⚙ Settings,
   ⬇ Download model, 📄 View logs, About, ✕ Quit. On macOS render the menu as
   a Liquid Glass popover.
3. **Dictation status indicator** — a small always-on-top floating pill (glass)
   that appears near the cursor or screen edge while listening/transcribing,
   showing the live state and a waveform. Auto-hides when idle. Optional and
   toggleable in settings.
4. **Settings window** — sections: General (start at login, start minimized,
   log level), Hotkey (key capture, push-to-talk toggle vs hold-to-talk),
   Audio (mic selector, sample rate, live level meter), Transcription (model
   picker with download/size, language, threads, extra args), Typing engine
   (auto / sendinput / ydotool / pyautogui with platform-appropriate options),
   Cleanup (capitalize, add period, collapse spaces toggles), About. Live
   preview of cleanup rules on a sample sentence. Changes apply on Save with
   an inline "Saved" toast; no restart needed.
5. **Logs window** — a clean, searchable, monospace log viewer with level
   filters and "Open log folder" / "Copy" actions.
6. **Empty/error states** — when no model is installed, when the mic is
   unavailable, when the focused app blocked typing. Each with a clear
   one-line cause and a single primary action.
7. **Update flow** — a subtle "New version available" glass banner in settings
   with Download / Dismiss; downloads the new installer from GitHub Releases.

### Interaction details to show

- Push-to-talk toggle (default): press hotkey → start, press again → stop.
  Hold-to-talk as an option.
- While listening, show the waveform + elapsed seconds in both the tray
  tooltip and the floating pill.
- On transcription complete, the typed text flows into the focused app; show a
  brief "⌨️ Typed 42 chars" confirmation that fades in 1.5s.
- On error, a non-blocking glass toast + tray warning icon; clicking opens the
  logs window at the relevant line.
- First-run onboarding launches automatically when no Whisper engine/model is
  configured (no manual `setup` command needed).

### Visual direction

- **Liquid Glass** as the signature: floating panels, the onboarding card, the
  status pill, and the tray popover are glass — translucent, with a faint
  top-edge specular highlight and content blurring through. Solid surfaces
  only for settings lists and log text areas where readability matters.
- Palette: neutral graphite base, a single accent (electric indigo #6366F1)
  used sparingly for the active/recording state and primary actions. Recording
  state adds a soft red glow. State colors: ready neutral, listening red,
  transcribing indigo, writing green, error amber.
- Typography: platform-native (Segoe UI / Inter / SF Pro). Numeric stats use
  tabular figures.
- Motion: springy 240ms for panel entry, 160ms for state changes; respect
  `prefers-reduced-motion`.
- Iconography: thin-stroke, 20–24px, consistent set across platforms.

### Deliverables to generate

For each of Windows, Linux, and macOS, produce: (a) the 3-step onboarding
flow, (b) tray menu + status pill in all five states, (c) settings window, (d)
logs window, (e) one empty/error state. Annotate platform-specific differences
(native chrome, menu placement, Liquid Glass on macOS vs acrylic on Windows
vs libadwaita on Linux). Include light and dark variants for the onboarding
and settings screens.
