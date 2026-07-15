# TAQANA Busbar Generator

A local web tool for generating copper busbar STEP files from engineering drawing dimensions.

---

## Requirements

- Windows 10 or 11 (64-bit)
- Internet connection (first install only)
- Miniconda (free, ~100 MB)

---

## Setup (one time only)

### Step 1 — Install Miniconda

Download and run the Miniconda installer for Windows:

**https://docs.conda.io/en/latest/miniconda.html**

Choose: **Miniconda3 Windows 64-bit**

During installation:
- Use default settings
- When asked about PATH, you can leave the default — the installer handles it

### Step 2 — Run install.bat

Double-click **install.bat** in this folder.

- This creates the Python environment with CadQuery and all dependencies
- Takes 10–20 minutes on first run (downloads ~500 MB)
- Only needs to be done once — even after restarts

If you see an SSL error, you may be on a corporate network.
Contact your IT department or try from a different network.

### Step 3 — Done

You're ready to use the tool.

---

## Starting the app

Double-click **run.bat**

A browser window will open automatically at `http://localhost:8000`.

To stop the app, close the terminal window or press Ctrl+C inside it.

---

## Using the tool

### Form mode
Fill in bar dimensions, segment lengths, bend angles, and hole features.
Click **Generate STEP + 3D preview** to run CadQuery and view the result.

### Direct Input mode
Click the **Direct Input** tab at the top.
Paste a Python input block directly and click **Parse + Generate**.

### Output files
Generated files are saved to the `output/` folder inside the app directory:
- `<filename>.step` — the STEP file for manufacturing
- `<filename>.stl` — used for the 3D preview in the browser

Files with the same name are overwritten each time you generate.

---

## Feature reference

| Letter | Type | Size |
|--------|------|------|
| a | Round hole | Ø11 mm |
| b | Round hole | Ø13 mm |
| c | Round hole | Ø14 mm |
| d | Round hole | Ø22 mm |
| h | Round hole | Ø5 mm |
| e | Compound slot | 13×18 mm |
| f | Compound slot | 9×14 mm |
| g | Compound slot | 11×15 mm |
| i | Custom slot | width × length (set in form) |
| j | Custom round | Ø (set in form) |
| k | Custom round 2 | Ø (set in form) |

---

## Troubleshooting

**run.bat says "busbar_python_path.txt not found"**
→ Run install.bat first

**run.bat says "Python not found at..."**
→ The environment was moved or deleted. Run install.bat again.

**Browser doesn't open automatically**
→ Open a browser manually and go to `http://localhost:8000`

**Generation fails with an error in the log**
→ Check the log text shown after generation — it contains the CadQuery error message.
   Common cause: a hole feature position is outside the segment boundary.

**SSL error during install.bat**
→ You may be on a corporate network with SSL inspection.
   Try: open Anaconda Prompt and run:
   `conda config --set ssl_verify false`
   Then run install.bat again.

---

## Updating

To get the latest version:
1. Download the new zip (or `git pull` if you used git)
2. Run **run.bat** — no reinstall needed unless told otherwise

---

## Built with

- [CadQuery](https://cadquery.readthedocs.io/) — parametric CAD geometry
- [FastAPI](https://fastapi.tiangolo.com/) — local web server
- [Three.js](https://threejs.org/) — 3D viewer

---

*TAQANA Energy Solutions — a Schneider Electric Joint Venture*
