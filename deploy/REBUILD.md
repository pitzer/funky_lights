# Rebuilding the Funklet Pi from a blank card

Follow this top to bottom on a fresh SD card. It targets **Raspberry Pi OS
Bookworm (64-bit) Lite** — the *Legacy* option in Imager — on a **Raspberry Pi 4 Model B**.

> **Why not the old setup notes.** The previous notes were written for Bullseye
> and will not run as-is: `libjasper-dev` and `libhdf5-103` no longer exist,
> Bookworm manages WiFi with NetworkManager rather than the `hostapd` guide those
> notes follow, and Bookworm's Python is "externally managed" so a bare
> `pip install` now fails. Each of those is handled below.

Everything marked **⚠ verify** could not be tested from a laptop — check it on
the hardware and correct this file.

---

## 1. Flash the card

Use **Raspberry Pi Imager**.

> ### Choose the Legacy (Bookworm) image, not the default
>
> Imager now offers *Raspberry Pi OS (64-bit)* built on Debian **Trixie**, with
> Bookworm demoted to *(Legacy)*. **Take the Legacy one.** Trixie ships Python
> 3.13, and this project's pins cannot be satisfied there:
>
> | Pin | Wheels published for | Trixie / Py 3.13 |
> |---|---|---|
> | `numpy<2` → 1.26.4 | cp39–cp312 | no wheel, and 1.x will not build on 3.13 |
> | `websockets<11` → 10.4 | cp37–cp311 | no wheel |
> | `opencv_python==4.5.5.62` | cp36, cp37, abi3 | installs, but is built against the numpy 1.x ABI |
>
> Bookworm's Python 3.11 is inside the support window for all three.
>
> Moving to Trixie later is a real but bounded piece of work, and it is a code
> change rather than a config one: allow `numpy>=2`, move to an OpenCV built
> against numpy 2 (4.10+), take `websockets>=14`, and then fix the WebSocket
> handler signatures — `serve(self, websocket, path)` in
> `controller/core/websockets.py` and `launchpadWSListener` in
> `controller/core/pattern_selector.py` both use the pre-11 two-argument form,
> which 14+ removed. Do that deliberately, not the night before an event.

Choose *Raspberry Pi OS Lite (64-bit) (Legacy)*, then open the advanced options
(gear icon, or ⌘⇧X) before writing:

| Setting | Value |
|---|---|
| Hostname | `funkletpi` |
| Username | `funklet` |
| Password | a new one — **do not reuse the old `funky`**, it is in a plaintext document |
| Enable SSH | yes — password authentication |
| Configure WiFi | **an existing network with internet** — your home WiFi or phone hotspot. **Not `funkletpi`.** |
| Wireless LAN country | your country (e.g. `US`) — required, see below |
| Locale / keyboard | as appropriate |

Two deliberate choices:

- **Hostname and SSID are both `funkletpi`**, so the Pi is reachable as
  `funkletpi.wlan` over its own AP. The *username* is different — `funklet` — and
  sets `/home/funklet`, which the supervisor config paths depend on.
- `main.py`'s `--pattern_mix_subscribe_uri` default still points at
  `ws://funkletpi.wlan:5680`, which is the *other* car. That is intentional and
  left alone; see the note at the end of this file.
- **Imager configures the Pi as a WiFi _client_, not an access point.** It has no
  option for AP mode; the `funkletpi` access point is created separately at step 7
  with `nmcli`. So the SSID you type here is a network you already have — put
  `funkletpi` in this box and the Pi will spend forever hunting for a network that
  does not exist yet.
- **Set bootstrap WiFi even though the Pi ends up as an access point**, and set
  the **wireless LAN country** while you are in there. Two separate reasons:
  - Steps 3-6 need internet — `apt full-upgrade`, `apt install`, `pip install`,
    `git clone`. Serial console alone will not get you through the build.
  - Filling in the WiFi fields is what sets the regulatory country. Leave it
    unset and `wlan0` stays soft-blocked (`Wi-Fi is currently blocked by
    rfkill`), and the access point at step 7 will refuse to start. This catches
    people out precisely because it looks like an AP problem, not a country one.

  The old notes said not to configure WiFi, since the Pi ends up as an AP. That
  is what left it unreachable. The bootstrap connection is temporary — the AP
  supersedes it at step 7, and step 7 turns its autoconnect off.

  Ethernet to a router works equally well for connectivity, but **still fill in
  the WiFi country** or the AP will not come up.

## 2. Enable the serial console before first boot

Do this while the card is still in your laptop. It is the rescue path when the
network is broken, and it costs nothing.

On the `bootfs` partition, append to `config.txt`:

```
enable_uart=1
```

`cmdline.txt` already contains `console=serial0,115200`. **⚠ verify** — confirm it
does; if not, add it, keeping the file to a single line.

To reach it later: USB-TTL adapter, GND→pin 6, adapter RX→pin 8, adapter TX→pin 10,
then `screen /dev/cu.usbserial-XXXX 115200`. Note a MacBook has no USB-A port, so
you need a USB-C adapter for this.

## 3. First boot and get in

```sh
ssh funklet@funkletpi.local          # or the address from your router
sudo apt update                      # required before step 4
sudo apt full-upgrade                # NOTE: no -y, see below
sudo reboot
```

> `apt update` is mandatory — step 4 installs stale or missing packages without
> it. `full-upgrade` is optional hygiene, and deliberately has no `-y`: if you are
> tethered to a phone hotspot it will pull several hundred MB of cellular data
> without asking. Without `-y` it prints the download size and waits. It may also
> pull a new kernel, so re-check the gadget console afterwards — that is the
> rescue path.

## 4. Dependencies

The old list was for building OpenCV from source. We install it as a wheel, so
most of it is unnecessary. What is actually needed:

```sh
sudo apt install -y \
    git python3-pip python3-venv python3-dev build-essential pkg-config \
    libgl1 libglib2.0-0 \
    supervisor vim
```

`libgl1` and `libglib2.0-0` are the runtime libraries `cv2` needs on a headless
image — without them `import cv2` fails with `libGL.so.1: cannot open shared
object file`, which is the most common failure here.

**⚠ verify** — if `opencv_python` decides to build from source rather than using a
piwheels wheel (it will take hours, so you will notice), stop and add the build
dependencies:

```sh
sudo apt install -y cmake gfortran libatlas-base-dev libhdf5-dev \
    libavcodec-dev libavformat-dev libswscale-dev libtiff-dev libjpeg-dev libpng-dev
```

Note `libtiff-dev`, not `libtiff5-dev`; and no `libjasper-dev`, which was dropped
from Debian years ago.

## 5. Clone the repository

`pitzer/funky_lights` is **public**, and the Pi only ever pulls, so no credential
is needed. Clone over HTTPS:

```sh
cd ~
git clone -b funklet https://github.com/pitzer/funky_lights.git
cd funky_lights
git branch --show-current      # MUST print: funklet
git log --oneline -1
```

> **`-b funklet` is not optional.** The repository's default branch is `main`,
> which is the full-size car:
>
> | | `main` | `funklet` |
> |---|---|---|
> | `config/led_config.json` | 5549 LEDs, 52 segments | 1443 LEDs, 14 segments |
> | `config/bus_config.json` | `{"led_busses": []}` | 2 OPC buses, `192.168.1.4/.5` |
>
> A bare `git clone` therefore gives you the wrong LED map *and* an empty bus
> list — the controller starts, renders 52 segments happily, logs a healthy
> 20 FPS, and sends the frames precisely nowhere. It fails silently rather than
> loudly, which is the worst kind. If `git branch --show-current` prints anything
> but `funklet`:
>
> ```sh
> git checkout funklet
> ```

It is a ~520 MB clone because of the video history, so run it inside `tmux` if
you are on a slow or metered link.

> **Do not put an SSH key on this Pi.** It lives in an art car and sits on an
> open-ish network at events. A deploy key or an account key would be standing
> credentials on a device you cannot physically secure, in exchange for access
> the repo already grants anonymously. If you ever need to push from the Pi, use
> a fine-grained token scoped to this one repo, at that moment, and remove it
> afterwards.

> The ed25519 key in the old setup notes was a *personal account* key stored in
> plaintext. It should be deleted from the GitHub account outright — replacing it
> on the Pi is not enough, since the copies in that document remain valid.

## 6. Python environment

Bookworm marks the system Python as externally managed (PEP 668), so
`pip install -e .` fails outright with `error: externally-managed-environment`.
Use a virtualenv — and note that supervisor must then call that interpreter
explicitly, not bare `python`.

```sh
python3 -m venv ~/venv
~/venv/bin/pip install --upgrade pip
~/venv/bin/pip install -e ~/funky_lights
~/venv/bin/python -c "import cv2, numpy, websockets; print(cv2.__version__, numpy.__version__, websockets.__version__)"
```

Expect `4.5.5 1.26.x 10.4`. The pins in `requirements.txt` matter: OpenCV is built
against the numpy 1.x ABI, and the WebSocket handlers use the pre-11 signature.

## 7. Networking

Two interfaces doing different jobs:

| Interface | Role | Network |
|---|---|---|
| `eth0` | to the two Teensy boards | `192.168.1.0/24` |
| `wlan0` | access point for laptops | `192.168.4.0/24`, Pi at `.1` |

### Ethernet to the boards

The boards sit at `192.168.1.4` and `.5`. **⚠ verify** whether they use static
addresses or DHCP — if static, the Pi needs a static address on that subnet too:

```sh
sudo nmcli connection add type ethernet ifname eth0 con-name funklet-boards \
     ipv4.method manual ipv4.addresses 192.168.1.1/24 autoconnect yes
sudo nmcli connection up funklet-boards
ping -c 3 192.168.1.4 && ping -c 3 192.168.1.5
```

No gateway is needed — this is a flat segment, not a route to anywhere.

### Access point on wlan0

Bookworm uses NetworkManager, so this is simpler than the old `hostapd` +
`dnsmasq` + `iptables` recipe. `ipv4.method shared` gives DHCP, DNS and NAT in
one setting, which replaces all three of the old `iptables` rules and
`iptables-persistent` entirely.

```sh
sudo nmcli connection add type wifi ifname wlan0 con-name funklet-ap \
     autoconnect yes ssid funkletpi

sudo nmcli connection modify funklet-ap \
     802-11-wireless.mode ap \
     802-11-wireless.band bg \
     ipv4.method shared \
     ipv4.addresses 192.168.4.1/24 \
     connection.autoconnect-priority 100

sudo nmcli connection modify funklet-ap \
     wifi-sec.key-mgmt wpa-psk wifi-sec.psk '<choose a passphrase>'

sudo nmcli connection up funklet-ap
```

> **The SSID is `funkletpi`, not `funkypi`.** The other art car uses `funkypi`.
> If both broadcast the same SSID at an event, a laptop associates with whichever
> is stronger and you can end up on the wrong elephant without noticing.

> **`wlan0` must never use `192.168.1.0/24`** — that belongs to `eth0`. Two
> interfaces on one subnet makes routing to the boards ambiguous, which produces
> intermittent faults that are very hard to trace.

> Run this **over serial or Ethernet**, not over the WiFi you are about to
> reconfigure. Bringing up the AP tears down your bootstrap connection.

### Restore the `.wlan` domain

The old `dnsmasq` supplied a `wlan` search domain, which is where `funkletpi.wlan`
comes from — including `main.py`'s default subscribe URI. NetworkManager's shared
mode does not do this by default. To keep those names working:

```sh
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
sudo tee /etc/NetworkManager/dnsmasq-shared.d/funklet.conf >/dev/null <<'EOF'
domain=wlan
local=/wlan/
address=/funkletpi.wlan/192.168.4.1
EOF
sudo nmcli connection down funklet-ap && sudo nmcli connection up funklet-ap
```

**⚠ verify** from a laptop on the AP: `ping funkletpi.wlan`. If it does not resolve,
use `192.168.4.1` directly and drop the `.wlan` references, or install `avahi-daemon`
and use `funkletpi.local`.

> ### ⚠ Pick an AP subnet that will not collide
>
> `192.168.4.0/24` is a very common default on consumer and travel routers, and
> `192.168.4.1` an equally common gateway. If the AP shares a subnet with a
> network you also use, you will at some point run diagnostics against the wrong
> device entirely — pinging fine, DNS answering, SSH refused — and conclude the Pi
> is broken when you were never talking to it. That happened during this build and
> cost a while.
>
> Prefer something unlikely to clash:
>
> ```sh
> sudo nmcli connection modify funklet-ap ipv4.addresses 192.168.42.1/24
> sudo nmcli connection up funklet-ap
> ```
>
> And before trusting any test against the AP, confirm what you are attached to:
>
> ```sh
> # on the laptop
> ipconfig getsummary en0 | grep ' SSID'      # must say funkletpi
> arp -n <gateway> | awk '{print $4}'         # MAC should be a Pi OUI:
> #   b8:27:eb  dc:a6:32  e4:5f:01  d8:3a:dd  2c:cf:67
> ```

### Retire the bootstrap connection

`wlan0` cannot be a client and an access point at the same time, so once the AP
is confirmed working, stop the bootstrap profile competing for the radio at boot.
Raspberry Pi Imager names its connection `preconfigured`:

```sh
nmcli -f NAME,TYPE,AUTOCONNECT connection show
sudo nmcli connection modify preconfigured connection.autoconnect no
```

Leave the profile in place rather than deleting it — it is a way back in if the
AP configuration ever breaks:

```sh
sudo nmcli connection up preconfigured     # temporarily rejoin your own network
```

### Turn off WiFi power save

Causes multi-second stalls on `wlan0`. It does not affect the LEDs — those are on
`eth0` — but it makes SSH and the visualizer drop out.

```sh
sudo nmcli connection modify funklet-ap 802-11-wireless.powersave 2
iw dev wlan0 get power_save
```

## 8. Supervisor

```sh
sudo cp ~/funky_lights/deploy/funklet-supervisor.conf \
        /etc/supervisor/conf.d/funky_lights.conf
sudo nano /etc/supervisor/conf.d/funky_lights.conf   # check user and paths
```

Note the old notes used `sudo echo "..." >> /etc/...`, which **does not work** —
the redirect runs as your unprivileged shell, not as root. Use `sudo tee` or an
editor.

Allow your user to drive supervisorctl, and expose the dashboard:

```sh
sudo nano /etc/supervisor/supervisord.conf
```

```ini
[unix_http_server]
chmod=0770
chown=root:funklet

[inet_http_server]
port=*:9001
```

> The dashboard has **no authentication**. That is acceptable on an AP you
> control; do not expose it on a network you do not.

```sh
sudo systemctl restart supervisor
sudo supervisorctl status
```

> ### ⚠ Exactly one controller at a time
> `funky_lights_controller_cached_mode` autostarts. Starting `live_mode` as well —
> or running `main.py` by hand while either is up — means two processes driving
> the same boards and interleaving frames from independent pattern rotations. It
> presents as stuttering, or different patterns on different segments.
> Check with `ps aux | grep '[m]ain.py'`.

## 9. Pattern cache

Cached mode is the autostart default, so build the cache before relying on it:

```sh
cd ~/funky_lights/controller
~/venv/bin/python create_pattern_cache.py
```

Roughly 31,000 files and ~150 MB, and it takes a while. It is keyed on a hash of
`config/led_config.json` — **any change to that file orphans it**, after which
every pattern logs `No cache found for pattern ...` and silently falls back to
live rendering. Rebuild it whenever the LED config changes.

## 10. Verify

```sh
# code
git -C ~/funky_lights branch --show-current   # funklet, not main
git -C ~/funky_lights log --oneline -1

# processes
sudo supervisorctl status                  # webserver + cached_mode running
ps aux | grep '[m]ain.py'                  # exactly one

# controller
tail -f ~/funklet.log                      # steady "Animation FPS: 20.0"
grep -i "OPC connection" ~/funklet.log     # both boards connected, no reconnect loop
grep -i "No cache found" ~/funklet.log     # should be empty after step 9

# network
iw dev wlan0 info | grep type              # type AP
ip -4 addr show wlan0                      # 192.168.4.1/24
ip -4 addr show eth0                       # 192.168.1.0/24
ping -c 3 192.168.1.4 && ping -c 3 192.168.1.5
```

From a laptop joined to `funkletpi`:

- <http://funkletpi.wlan:9001/> — supervisor dashboard
- <http://funkletpi.wlan:8000/visualization/index.html> — visualizer
- <http://funkletpi.wlan:8000/visualization/index.html?debug=index> — LED order check

## 11. Afterwards

- **Decide what `--pattern_mix_subscribe_uri` should point at.** Its default is
  `ws://funkypi.wlan:5680` — the *other* car, not this Pi. Left as-is on purpose;
  see "Following the other car" in [FUNKLET.md](../FUNKLET.md).
- **Rotate the old key.** The ed25519 key in the previous setup notes was stored
  in plaintext and should be deleted from the GitHub account entirely. Nothing on
  this Pi needs it — the clone is anonymous HTTPS.
- **Keep the account password and the AP passphrase out of this repo.** The
  remote is public. Keep them in a password manager.
- **Consider switching SSH to keys** once things are running. It needs no
  re-image — one command from your laptop, and the password stops being the thing
  standing between an event WiFi network and a shell:
  ```sh
  ssh-copy-id funklet@funkletpi.wlan
  # then, optionally, on the Pi:
  #   sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  #   sudo systemctl restart ssh
  ```
- **Take an image of the finished card** so the next rebuild is a restore:
  ```sh
  # on a laptop, with the card inserted; check the disk number first
  sudo dd if=/dev/rdisk4 bs=4m | gzip > funklet-$(date +%Y%m%d).img.gz
  ```
- Consider a card with better endurance. The previous one failed after a period
  of suspected brownouts, and power loss during writes is a common way SD cards
  die.
