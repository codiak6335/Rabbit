# Rabbit Desktop Emulators

This adds local emulators for:
- LED strand (`neopixel` state + visual grid)
- OLED/TFT display text output
- Web interface (the existing Rabbit UI served by `main.py`)

## Run

From repo root:

```bash
python3 emulator/run_desktop_emulator.py
```

Then open:
- Emulator viewer: `http://127.0.0.1:8081`
- Rabbit web UI: `http://127.0.0.1:8080`

## Notes

- Hardware-specific MicroPython modules are stubbed from `emulator/stubs/`.
- Absolute runtime paths like `/db/pools.json` are redirected to `./db/pools.json`.
- `main.py` still runs as-is; the launcher only patches runtime behavior for desktop emulation.
