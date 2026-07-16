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
