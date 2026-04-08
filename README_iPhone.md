# iPhone Play Guide

This repository now includes an iPhone/Web build entry:

- `game_v3.py`: original desktop version
- `game_v3_ios.py`: mobile/web adapted version
- `main.py`: web build entry for `pygbag`

## What changed

- The iPhone version keeps the same poker logic.
- Rendering is scaled to fit the browser window.
- Touch input is supported.
- Betting now has touch-friendly quick buttons: `Clear`, `Min`, `1/2 Pot`, `Pot`, `All-in`.

## Local desktop test

```powershell
python game_v3_ios.py
```

## Build as an iPhone-playable web app

1. Install web build dependencies:

```powershell
pip install -r requirements-web.txt
```

2. Build the browser version:

```powershell
pygbag --build .
```

3. After build completes, publish the generated web output folder to any static host.
   Common options: GitHub Pages, Netlify, Vercel, or your own web server.

4. On iPhone:
   Open the published URL in Safari.
   Use `Share -> Add to Home Screen`.

## Important limitation

This is not a native `.ipa` iOS app package. It is a browser app packaged for iPhone use. That is the practical route from an existing `pygame` project without rebuilding the whole game in Swift or another native/mobile framework.
