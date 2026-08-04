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
- [Updating the code on the Pi](#updating-the-code-on-the-pi)
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

**Both boards are wired to the Pi over Ethernet**, not WiFi — `192.168.1.0/24`
lives on `eth0`. The Pi's `wlan0` is separate and is only how *you* reach the Pi;
LED traffic never touches it. Note that the *defaults* in
`main.py` (`../config/led_config.json`, `../config/bus_config.json`) are already
the Funklet ones on this branch — you do not need to pass `-l` or `-b` in the field.

The 14 segments are: `ear_right`, `head`, `ear_left`, `leg_back_left`,
`leg_back_right`, `leg_front_left`, `leg_front_right`, `tail`, `trunk`, `dome`,
`ball`, `tusks`, `eyes_right`, `eyes_left`. The two eye segments are 16x16 LED
matrices (256 LEDs each).

---

## Connecting and SSH

The Pi has two networks and they do different jobs:

| Interface | Network | Carries |
|---|---|---|
| `eth0` | `192.168.1.0/24` | LED data to both boards |
| `wlan0` | whatever the Pi joins or broadcasts | how you reach the Pi |

You do **not** need to be on `192.168.1.0/24` to work on the sculpture. That
segment sits behind the Pi; from your laptop you will usually have no route to
`192.168.1.4`/`.5` at all, and that is fine and expected. Reach the Pi over
`wlan0`, and check the boards *from the Pi*.

> **Unverified:** whether `wlan0` broadcasts its own network or joins one from a
> separate router is not recorded anywhere in this repo. The `.wlan` suffix in
> `main.py` is a DHCP-supplied domain, not mDNS, so something is running a DNS
> server — either the Pi or a router. Determine which and correct this section:

```sh
# On the Pi
iw dev wlan0 info | grep type         # "type AP" vs "type managed"
ip -4 addr show wlan0                 # the address you will SSH to
ip -4 addr show eth0                  # should be on 192.168.1.0/24
```

1. **Get on the Pi's WiFi.** If the Pi is the AP, join the SSID it broadcasts;
   otherwise join the router's. Then, *once on the Pi*, confirm it can see both
   boards over Ethernet:

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

4. **Check WiFi power save.** Worth doing once on any new Pi. Power save causes
   multi-second stalls on `wlan0`. This does *not* affect the LEDs — they are on
   `eth0` — but it makes SSH and the visualizer drop out, and a stalled SSH pty
   can block the controller if you launched it by hand (see the note below):

   ```sh
   iw dev wlan0 get power_save
   sudo iw dev wlan0 set power_save off                      # for this boot
   sudo nmcli connection modify <name> wifi.powersave 2      # persist it
   ```

> **Run the controller under systemd, not in your SSH session.** If you launch it
> by hand and your SSH connection stalls, writes to the terminal can block the
> process. See [Running the controller](#running-the-controller).

> WiFi clients do not compete with LED traffic — the boards are on `eth0`. The
> visualizer is still ~1.3 MB/s over WiFi, so it can saturate a weak link and make
> your own SSH session unresponsive, but it cannot disturb the sculpture.

### SSH to the Pi over its own WiFi

`sshd` is enabled on this card, so if you cannot get in after joining the Pi's
network, sshd is not the problem — the addressing is.

**Once you have joined the Pi's SSID, the Pi is your gateway.** That is the
reliable way to find its address without knowing which subnet it chose:

```sh
# macOS (use en1 etc. if your WiFi is not en0)
ipconfig getoption en0 router
route -n get default | grep gateway

# Linux
ip route | awk '/default/ {print $3}'
```

Then connect:

```sh
ssh pi@<that address>
```

With NetworkManager's default hotspot the address is `10.42.0.1`, so in practice:

```sh
ssh pi@10.42.0.1
```

> It will **not** be a `192.168.1.x` address. That subnet belongs to `eth0` and
> the boards, and is not reachable from a WiFi client. If you try `192.168.1.x`
> and it hangs, that is why — nothing is broken.

Confirm you are actually on the Pi's own network rather than some other one:

```sh
ipconfig getsummary en0 | grep SSID    # macOS: which network am I on?
```

Once in, `ip -4 addr show wlan0` on the Pi shows the address it is serving, and
`ip -4 addr show eth0` should show `192.168.1.x` for the boards.

#### If the Pi is not broadcasting a network yet

Check first — `iw dev wlan0 info` reports `type AP` if it already is, in which
case there is nothing to configure.

If it is not, this is straightforward: because the boards are on Ethernet, an
access point on `wlan0` is completely independent of them, and nothing you do to
the WiFi can strand the boards. The one-liner is fine:

```sh
sudo nmcli device wifi hotspot ifname wlan0 ssid Funklet password "<choose one>"
sudo nmcli connection modify Hotspot connection.autoconnect yes \
     connection.autoconnect-priority 100
```

That puts `wlan0` on `10.42.0.1/24` with NetworkManager running dnsmasq for DHCP,
and `autoconnect` brings it back automatically on every boot. Join the SSID and
`ssh pi@10.42.0.1`.

> **The AP must not use `192.168.1.0/24`.** That subnet already belongs to `eth0`.
> Putting `wlan0` on it too gives the Pi two interfaces on one subnet, and routing
> to the boards becomes ambiguous — which is a good way to make the sculpture
> intermittently unreachable for reasons that are hard to see. The `10.42.0.0/24`
> default avoids this; if you change it, pick anything except `192.168.1.0/24`.

You do not need routing or forwarding between the two interfaces. You SSH to the
Pi over `wlan0`; the controller talks to the boards over `eth0`. The Pi is on both
networks at once and that is all it needs to be.

> **Do this with the serial console connected, never over SSH.** Bringing up an AP
> profile tears down whatever WiFi connection you are using, so a mistake locks
> you out of the machine you are fixing. Serial is unaffected by any of it —
> that is what makes it worth having set up.

Afterwards, verify from the Pi before trusting it:

```sh
iw dev wlan0 info | grep type          # expect: type AP
ip -4 addr show wlan0                  # expect: 10.42.0.1/24
ip -4 addr show eth0                   # must still be on 192.168.1.0/24
ping -c 3 192.168.1.4                  # boards must still be reachable
ping -c 3 192.168.1.5
```

To undo:

```sh
sudo nmcli connection down Hotspot && sudo nmcli connection delete Hotspot
```

---

## Updating the code on the Pi

The checkout lives at `~/funky_lights`. Two routes, depending on whether the Pi
can reach the internet.

### Always do this first

```sh
cd ~/funky_lights
git branch --show-current       # expect: funklet
git log --oneline -1            # where the Pi actually is
git status                      # any local edits?
```

If `git status` is dirty, keep the changes rather than losing them:

```sh
git stash push -m "pre-update local changes"
```

### If the Pi has internet

```sh
git pull --ff-only origin funklet
```

`--ff-only` refuses rather than creating a merge commit if the Pi has diverged.
If it refuses, stop and look at `git log --oneline origin/funklet..funklet` —
something was committed on the Pi that is not upstream.

### If the Pi has no internet (offline bundle)

A git bundle can be staged on the SD card's boot partition, which the Pi reads at
`/boot/firmware/`. This carries real commits, not a patch, so history stays intact.

To build one, on a machine that has the commits:

```sh
git bundle create /Volumes/bootfs/funklet-update.bundle <pi-current-commit>..funklet
git bundle verify /Volumes/bootfs/funklet-update.bundle
```

To apply it, on the Pi:

```sh
git fetch /boot/firmware/funklet-update.bundle funklet:funklet-update
git log --oneline funklet..funklet-update      # review before merging
git merge --ff-only funklet-update
git branch -d funklet-update                   # tidy up afterwards
```

The bundle records its starting commit as a prerequisite, so if the Pi is not
where you expected, the fetch fails cleanly with "Repository lacks these
prerequisite commits" rather than applying something half-valid.

### After updating, either way

```sh
git stash pop                   # only if you stashed
pip install -e .                # pins changed: numpy<2, websockets<11
```

The `pip install` is not optional if the environment predates those pins — an
environment with numpy 2.x cannot import `cv2` at all, and the controller will
not start.

Then restart the controller. Check for a stale instance first; two controllers
running at once will fight over the boards:

```sh
ps aux | grep '[m]ain.py'
sudo systemctl restart funklet-controller     # if running as a service
```

Verify it came back:

```sh
tail -f ~/funklet.log           # expect a steady "Animation FPS: 20.0"
```

### Rolling back

```sh
git reset --hard <previous-commit>
pip install -e .                # only if requirements changed between the two
```

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

Be aware this streams a 64 KB texture 20 times a second (~1.3 MB/s) over WiFi.
That is well clear of the LED data, which goes out over `eth0`, but it is a lot
for a WiFi link at an event and will make your SSH session sluggish. Prefer
running the controller and visualizer locally when you are working on patterns,
and treat the remote view as a spot check rather than something to leave open.

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
Both boards hold their last frame whenever the controller stops sending. Check
`grep "OPC connection" ~/funklet.log` for timestamps and the disconnect reason.
Since the boards are wired, a simultaneous outage is *not* a WiFi problem — look
at what they share: the Ethernet switch, its power, the Pi's `eth0`, or the Pi
itself stalling. A stalled event loop (blocking terminal writes, a clock step)
freezes every bus at once and is worth ruling out first via the log.
The disconnect reason is diagnostic: `None` means the board closed the connection
cleanly, `ConnectionResetError` means it reset, and a timeout means the link died.

**Half the sculpture freezes.**
One board only — check that board's IP with `ping`, and look for its address in
the OPC log lines. `board_1` is the trunk/front-legs/head side, `board_2` is the
dome/tail/tusks/eyes side. Independent per-board failures point at something
board-specific — power, or a board reset — rather than the network, since a
switch or cabling fault would usually take both down together.

**It got worse after adding people or laptops to the network.**
This will not affect the LEDs — the boards are wired — but the visualizer is
~1.3 MB/s over WiFi and will make your own SSH session crawl. Close it when you
are not watching it.

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
