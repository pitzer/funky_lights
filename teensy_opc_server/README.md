# Funklet Teensy OPC server

Firmware for the two Teensy 4.1 boards that drive Funklet's LEDs. Each listens
on TCP **7890** and maps Open Pixel Control channels onto OctoWS2811 outputs.

**Reconstructed, not original.** The firmware that shipped on these boards is
not in this repository, and Teensy flash cannot be read back — the bootloader is
write-only by design. This was rebuilt from `controller/core/opc.py`,
`config/bus_config.json` and `config/led_config.json`. See the header comment in
the `.ino` for what is derived and what is assumed.

## Build

Standard PlatformIO layout — source in `src/`, one env per board.

```sh
pio run -e board2 -t upload      # the 192.168.1.5 board
pio run -e board1 -t upload      # the 192.168.1.4 board
pio device monitor               # 115200
```

The env sets `-D BOARD=1` or `2`, which selects the static IP, channel count
and per-strip lengths. Nothing else differs between the two boards, and you do
not edit source to switch targets.

> If you copy this into an existing PlatformIO project, make sure you do not
> end up with **two** files defining `setup()`/`loop()` — a leftover
> `src/main.cpp` stub alongside this one gives
> `multiple definition of 'setup'` at link time. Check with:
> `grep -rn "void setup" --include=*.cpp --include=*.ino .`

## Wiring

Pins are OctoWS2811's Teensy 4.x defaults, and OPC channel number equals board
position:

| ch | pin | board_1 (192.168.1.4) | LEDs | board_2 (192.168.1.5) | LEDs |
|---|---|---|---|---|---|
| 1 | 2  | tail            | 54  | dome      | 181 |
| 2 | 14 | leg_front_right | 74  | ball      | 33  |
| 3 | 7  | leg_back_right  | 80  | eyes_left | 256 |
| 4 | 8  | leg_front_left  | 82  | tusks     | 2   |
| 5 | 6  | leg_back_left   | 89  | ear_left  | 68  |
| 6 | 20 | eyes_right      | 256 | trunk     | 134 |
| 7 | 21 | —               |     | ear_right | 69  |
| 8 | 5  | —               |     | head      | 65  |

These come from `config/bus_config.json` (channel = index of uid + 1) and
`config/led_config.json`. **If either config changes, this table and the
`kChannelLen` arrays must change with it** — nothing checks that they agree.

## Bring-up

Flash, connect **Ethernet only**, and watch the Pi:

```sh
tail -f ~/funklet.log
grep -i "OPC connection" ~/funklet.log
```

You want the connection to establish and stay up — no reconnect loop, no
`stalled for over 2.0s` messages. That exercises the network and protocol with
no LED risk. Only then connect strips.

## Known unknowns

- **Colour order** is assumed `WS2811_GRB`. If red and green are swapped
  everywhere, change `kLedConfig`. If only the tusks are wrong, that is a
  per-strip difference — the controller used to carry a green/blue swap for that
  segment, which has since been removed.
- **Cut the VUSB pad** before a board that has been programmed over USB goes
  into a system with external 5 V.
