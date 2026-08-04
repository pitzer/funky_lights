# Funklet

Funklet is the small elephant. It runs the same controller as the full-size
Funkadelephant but is a separate installation with its own LED map and its own
transport: **1443 LEDs across 14 segments**, driven entirely over the network by
two Teensy 4.1 boards speaking [Open Pixel Control](http://openpixelcontrol.org/).

This is the Funklet-specific guide. For the attiny85 boards, bootloader, fuses,
and the full-size car, see [README.md](README.md).

> Funklet does **not** use the attiny85 / USB-serial buses that most of the main
> README describes. Its two buses are both OPC over TCP.

---

## Contents

- [Hardware and addressing](#hardware-and-addressing)
- [Connecting and SSH](#connecting-and-ssh)
- [Running the controller](#running-the-controller)
- [Running the visualizer](#running-the-visualizer)
- [Pattern cache](#pattern-cache)
- [Local development without hardware](#local-development-without-hardware)
- [Regenerating the LED config](#regenerating-the-led-config)
- [Troubleshooting](#troubleshooting)

---

## Hardware and addressing

| Thing | Value | Where it's defined |
|---|---|---|
| LED config | 1443 LEDs, 14 segments | [config/led_config.json](config/led_config.json) |
| Bus config | 2 OPC buses, no serial | [config/bus_config.json](config/bus_config.json) |
| `board_1` | `192.168.1.4:7890` — uids 12, 114, 17, 18, 16, 271 | [config/bus_config.json](config/bus_config.json) |
| `board_2` | `192.168.1.5:7890` — uids 21, 214, 272, 28, 26, 220, 221, 25 | [config/bus_config.json](config/bus_config.json) |
| Controller host | a Raspberry Pi, conventionally `funkypi` | default in [main.py](controller/main.py) is `ws://funkypi.wlan:5680` |

Both boards sit on the same WiFi network as the Pi. Note that the *defaults* in
`main.py` (`../config/led_config.json`, `../config/bus_config.json`) are already
the Funklet ones on this branch — you do not need to pass `-l` or `-b` in the field.

The 14 segments are: `ear_right`, `head`, `ear_left`, `leg_back_left`,
`leg_back_right`, `leg_front_left`, `leg_front_right`, `tail`, `trunk`, `dome`,
`ball`, `tusks`, `eyes_right`, `eyes_left`. The two eye segments are 16x16 LED
matrices (256 LEDs each).

---

## Connecting and SSH

> **Unverified.** Nothing in this repo records the network topology — no
> `hostapd`, `dnsmasq`, or `wpa_supplicant` config is checked in. The only
> evidence is that the boards live on `192.168.1.0/24` and that the controller
> defaults to `ws://funkypi.wlan:5680`. Whether the Pi *broadcasts* that network
> or *joins* one served by a separate router is not captured anywhere. Confirm it
> against the hardware and correct this section.

The `.wlan` suffix is a DHCP-supplied domain (a `dnsmasq`/router `domain=` setting),
not mDNS — so something on the network is running a DNS server. That is either the
Pi itself acting as an access point, or a separate router. To tell which:

```sh
# On the Pi: is it serving the network, or joining one?
systemctl status hostapd dnsmasq      # active => the Pi is the AP
iw dev wlan0 info | grep type         # "type AP" vs "type managed"
ip route | grep default               # no default route via another host => likely the AP
ip -4 addr show wlan0                 # an AP is usually .1 on its own subnet
```

1. **Join the Funklet network.** Either way, you need to be on the same
   `192.168.1.0/24` network as the boards. If the Pi is the AP, join the SSID it
   broadcasts; otherwise join the router's. Then confirm you can see everything:

   ```sh
   ping -c 3 192.168.1.4     # board_1
   ping -c 3 192.168.1.5     # board_2
   ```

2. **SSH to the Pi.** The account on this installation is `pi` (confirmed against
   the hardware — note this is *not* an OS default: Raspberry Pi OS has had no
   default `pi` user since April 2022, so on a rebuilt card it will be whatever
   Imager was told to create. Check with `whoami`.)

   ```sh
   ssh pi@funkypi.wlan       # the name the controller itself uses
   ssh pi@funkypi.local      # if Avahi/mDNS is set up instead
   ssh pi@192.168.1.<addr>   # by address
   ```

   Find the Pi's address from another machine on the network with:

   ```sh
   arp -a | grep -i b8:27:eb    # Raspberry Pi Foundation OUI
   arp -a | grep -i dc:a6:32    # newer Pi 4 OUI
   ```

   If the Pi is the AP, its own address is the network's gateway — `ip route` on
   your laptop after joining will name it.

3. **Credentials are deliberately not recorded here.** This repository has a
   public GitHub remote, so anything committed to it is published — a password in
   this file would be a password on the internet, and rewriting history does not
   reliably unpublish it. Keep the account password out of the repo, out of the
   boot partition, and out of commit messages.

   Set up key-based login once and you will not need the password again:

   ```sh
   ssh-keygen -t ed25519                  # if you do not already have a key
   ssh-copy-id <user>@funkypi.wlan        # asks for the password one last time
   ```

   Then consider disabling password authentication on the Pi entirely
   (`PasswordAuthentication no` in `/etc/ssh/sshd_config`), which matters more
   than usual if the Pi is broadcasting its own network at an event.

> If the Pi *is* the access point, remember that every client you attach shares
> the radio that is feeding the two boards ~100 KB/s. An SSH session is
> negligible; running the visualizer over that link is not. See
> [Troubleshooting](#troubleshooting).

3. **Check WiFi power save.** This is worth doing once on any new Pi. Power save
   causes multi-second network stalls, which show up as the whole sculpture
   freezing:

   ```sh
   iw dev wlan0 get power_save
   sudo iw dev wlan0 set power_save off                      # for this boot
   sudo nmcli connection modify <name> wifi.powersave 2      # persist it
   ```

> **Run the controller under systemd, not in your SSH session.** If you launch it
> by hand and your SSH connection stalls, writes to the terminal can block the
> process. See [Running the controller](#running-the-controller).

---

## Running the controller

### As a service (how it should run in the field)

```sh
sudo cp deploy/funklet-controller.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now funklet-controller
```

Edit `User`, `WorkingDirectory`, and `ExecStart` in the unit file to match the
Pi before installing it. Then:

```sh
systemctl status funklet-controller
journalctl -u funklet-controller -f      # live output
sudo systemctl restart funklet-controller
```

The service restarts automatically if the controller exits.

### By hand (for debugging)

```sh
cd controller
python main.py
```

Useful flags:

| Flag | Meaning |
|---|---|
| `-a, --animation_rate` | Target frame rate in Hz (default `20`) |
| `-c, --enable_cache` | Play patterns from the on-disk cache — see [Pattern cache](#pattern-cache) |
| `--pattern_rotation_time` | Seconds before auto-advancing to the next pattern (default `600`) |
| `--enable_launchpad` | Enable the USB Launchpad Mini MK3 controller |
| `--log_file` | Rotating log file (default `~/funklet.log`); pass `''` to disable |
| `-l`, `-b` | Override the LED / bus config files |

### Logs

The controller writes to `~/funklet.log` (rotating, 20 MB x 5) as well as the
console. When something goes wrong, that file is the first place to look:

```sh
tail -f ~/funklet.log
grep -i "OPC connection" ~/funklet.log      # board connects/disconnects
grep -i "Fell behind"    ~/funklet.log      # dropped frames
grep -i "Animation FPS"  ~/funklet.log      # should read ~20.0
```

A healthy log looks like a steady stream of `Animation FPS: 20.0` with no
`OPC connection ... lost` lines in between.

---

## Running the visualizer

The controller streams every frame over WebSockets whether or not the boards are
connected, so the visualizer works from your laptop with no hardware attached.

The page fetches `../config/led_config.json`, so it must be served over HTTP from
the **repository root** — opening the file directly with `file://` will fail.

1. Start the controller (see above).

2. Serve the repo root:

   ```sh
   cd /path/to/funky_lights
   python -m http.server 8000
   ```

3. Open <http://localhost:8000/visualization/index.html>.

The page connects to `ws://<same-host>:5678` for LED data and `ws://<same-host>:5679`
for the on-screen Launchpad. Both auto-reconnect, so you can restart the
controller without reloading the page.

To watch the Pi's output from your laptop, run the HTTP server *on the Pi* and
browse to `http://funkypi.wlan:8000/visualization/index.html` — the page derives
the WebSocket host from the page URL, so ports 5678/5679 must be reachable too.

Be aware this streams a 64 KB texture 20 times a second (~1.3 MB/s) over the
network, on top of the ~100 KB/s already going to the boards. If the Pi is also
the access point, that all shares one radio. Prefer running the controller and
visualizer locally when you are working on patterns, and treat the remote view as
a spot check rather than something to leave open.

### Checking LED order and direction

```
http://localhost:8000/visualization/index.html?debug=index
```

`?debug=index` paints each segment with a hue ramp along its LED index instead of
showing live frames. Use it to confirm each segment starts at the right physical
end after rewiring — see `tools/set_segment_start.py` for adjusting `reversed`
and `offset`.

---

## Pattern cache

Patterns can be pre-rendered to disk and played back instead of computed live.
This trades CPU for disk I/O, which is useful when the Pi cannot keep up with
live video decoding.

### Building the cache

```sh
cd controller
python create_pattern_cache.py
```

| Flag | Meaning |
|---|---|
| `-m, --max_cached_pattern_duration` | Seconds to render per pattern (default `60`) |
| `-a, --animation_rate` | Frames per second (default `20`) — **must match** the rate you run `main.py` at |
| `-f, --force_update` | Re-render patterns that are already cached |
| `-l, --led_config` | LED config to render against |

### Playing from the cache

```sh
cd controller
python main.py -c
```

### Where it lives, and how it is keyed

The cache is written to your **home directory**, not into the repo:

```
~/pattern_cache/<led_config_hash>/<pattern_id>/<000000-000999>/<000000>.p
```

`<led_config_hash>` is a SHA-256 of the entire LED config JSON. This is the part
that surprises people:

> **Any change to `config/led_config.json` changes the hash and orphans the whole
> cache.** The controller does not fail — it logs `WARNING: no cache found for
> pattern <id>` for each pattern and silently falls back to live rendering. If you
> regenerate the LED config, you must rebuild the cache.

The current config hashes to `fe3eee5e...`; check yours with:

```sh
cd controller && python -c "
import json; from core.pattern_cache import hash_led_config
print(hash_led_config(json.load(open('../config/led_config.json'))))"
```

Old caches are never cleaned up automatically. Delete stale ones by hand:

```sh
du -sh ~/pattern_cache/*
rm -rf ~/pattern_cache/<old_hash>
```

### Size

At the default 60 seconds x 20 Hz across all 26 patterns, expect roughly
**31,000 files and ~150 MB** for the Funklet config (~4.9 KB per frame). The
index file for each pattern is written *last*, so an interrupted build is
correctly treated as incomplete and re-rendered on the next run.

### Caveats

- Playback reads one pickle file per frame (20 reads/second). On a slow or worn
  SD card this can stall the controller, which is the opposite of what you want.
  Measure before enabling it in the field.
- Caching makes random patterns deterministic. The special-effect patterns
  (`0x7` flash, `1x7` sparkle, `2x7` checkers, `3x7` starburst) become a fixed
  60-second loop rather than being generated fresh.
- `segment_masks` do not survive the cache round-trip. They are written to
  `index.json` as plain JSON arrays and restored *after* `prepareSegments()` has
  already run, so they are never applied. No pattern in the current
  `DEFAULT_CONFIG` uses them, so this is latent — but do not rely on masks in a
  cached pattern without fixing it first. `include_segments` and
  `exclude_segments` do round-trip correctly (the eyes pattern depends on this).

---

## Local development without hardware

You do not need the boards to work on patterns. Install into a virtualenv:

```sh
cd /path/to/funky_lights
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The version pins in `requirements.txt` matter — see the comments in that file.
Briefly: OpenCV is pinned to a build compiled against the numpy 1.x ABI, and the
WebSocket handlers use the pre-11 `(websocket, path)` signature.

Then run the controller with an empty bus list so it does not try to reach the
boards:

```sh
echo '{ "led_busses": [] }' > /tmp/bus_local.json
cd controller
python main.py -b /tmp/bus_local.json
```

and view it in the [visualizer](#running-the-visualizer). Everything except the
actual LED output works: patterns render, rotation runs, the Launchpad UI
responds.

Running against the real `config/bus_config.json` off-network also works — the
controller retries the boards with exponential backoff (0.25s up to 5s) and keeps
animating regardless — but it will log connection failures continuously.

---

## Regenerating the LED config

`config/led_config.json` is generated from the CAD-derived polylines in
`config/funklet/funklet_actual.csv` by
[tools/generate_led_config_funklet.ipynb](tools/generate_led_config_funklet.ipynb).

Supporting tools:

- `tools/set_segment_start.py` — inspect or set `reversed` / `offset` per segment,
  to move LED 0 to the right physical end after rewiring.
- `tools/repair_funklet_polylines.py` — repairs point-order corruption in the CAD
  polylines (a merge-order bug in `generate_csv_from_fusion_sketch.py` dropped the
  leading point of each entity).

After regenerating, remember to:

1. Check `config/bus_config.json` still lists every segment uid.
2. Verify LED order in the visualizer with `?debug=index`.
3. **Rebuild the pattern cache** if you use `-c` — the hash will have changed.

---

## Troubleshooting

**The whole sculpture freezes for a few seconds, then resumes.**
Both buses ride the same WiFi radio, so a network blip drops them together and
the boards hold their last frame until the controller reconnects. Check
`grep "OPC connection" ~/funklet.log` for the timestamps and the disconnect
reason. Then check WiFi power save (see [Connecting and SSH](#connecting-and-ssh)).
The disconnect reason is diagnostic: `None` means the board closed the connection
cleanly, `ConnectionResetError` means it reset, and a timeout means the link died.

**Half the sculpture freezes.**
One board only — check that board's IP with `ping`, and look for its address in
the OPC log lines. `board_1` is the trunk/front-legs/head side, `board_2` is the
dome/tail/tusks/eyes side. Independent per-board failures point at something
board-specific (power, a reset) rather than the network, since a WiFi problem
takes both buses down together.

**It got worse after adding people or laptops to the network.**
If the Pi is the access point, every client shares the radio that is feeding the
boards. The visualizer in particular is ~1.3 MB/s — an order of magnitude more
than the LED data itself. Close it when you are not watching it.

**`Fell behind: skipped N frame(s)` in the log.**
The render loop is not keeping up. Most likely video decoding — 14 of the 16
rotation patterns are `VideoPattern`, and OpenCV decoding runs on the same thread
as everything else. Try `--enable_cache`, or lower `--animation_rate`.

**`WARNING: no cache found for pattern <id>`.**
The LED config changed since the cache was built. Rebuild it — see
[Pattern cache](#pattern-cache).

**The visualizer is blank.**
Check the browser console. If `led_config.json` 404s, you are serving from the
wrong directory — it must be the repository root, not `visualization/`.

**`ModuleNotFoundError: No module named 'funky_lights'`.**
Run `pip install -e .` from the repository root.
