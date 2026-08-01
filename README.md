# Rabbit
Underwater LED system for swimmers 

https://www.thingiverse.com/thing:4129039


requires micropython-logging-0.5.2 installed under /lib/logging as a module

## Desktop emulator

Run the web UI and LED emulator locally without flashing the microcontroller:

```bash
RABBIT_EMULATOR=1 python3 main.py
```

Then open:

- `http://localhost:5000/` for the normal control UI
- `http://localhost:5000/emulator` for the control UI plus the live LED/display emulator

If you need a different bind address or port:

```bash
RABBIT_EMULATOR=1 RABBIT_HOST=0.0.0.0 RABBIT_PORT=5000 python3 main.py
```

## Admin token

Set `RABBIT_ADMIN_TOKEN` to require a token for control and config-write routes:

```bash
RABBIT_ADMIN_TOKEN=change-me python3 main.py
```

Open the UI with `?token=change-me` once, or send `X-Rabbit-Token: change-me` from API clients.

## Structured workouts

Coach On Deck supports versioned DeckScript workouts alongside the original Pace and Sprint set paths. See [DeckScript 2](docs/deckscript.md) for timing semantics, nested rounds, progressions, negative splits, shorthand import, and the compact RP2 execution format.

## RP2 compatibility check

Before copying a new build to the controller, test its production imports
against the connected MicroPython runtime:

```bash
python3 tools/smoke_rp2040.py --device /dev/ttyACM0
```

The check mounts the working tree without overwriting the controller, imports
the production runtime modules, verifies device-mode path handling, and then
reboots the existing on-device application.
