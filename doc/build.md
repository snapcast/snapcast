# Build Snapcast

## Clone the Snapcast repository

To do this, you need git.  
For Debian derivates (e.g. Raspberry Pi OS, Debian, Ubuntu, Mint):

```sh
sudo apt-get install git
```

For Arch derivates:

```sh
sudo pacman -S git
```

For FreeBSD:

```sh
sudo pkg install git
```

Clone Snapcast:

```sh
git clone https://github.com/snapcast/snapcast.git
```

## Install dependencies

Snapcast depends on boost 1.74 or higher. Since it depends on header only boost libs, boost does not need to be installed, but the boost include path must be set properly: download and extract the latest boost version and tell `cmake` the path using the `-DBOOST_ROOT` flag: `cmake -DBOOST_ROOT=/path/to/boost_1_8x_0`.

### For Debian derivates (e.g. Raspberry Pi OS, Debian, Ubuntu, Mint)

```sh
sudo apt-get install build-essential cmake cmake-format ccache ninja-build
sudo apt-get install alsa-utils avahi-daemon libasound2-dev libavahi-client-dev libboost-dev libexpat1-dev libflac-dev libjack-dev libopus-dev libpulse-dev libsoxr-dev libssl-dev libvorbis-dev libvorbisidec-dev
```

### For Arch derivates

```sh
sudo pacman -S base-devel cmake
sudo pacman -S alsa-lib avahi libvorbis opus-dev flac libsoxr alsa-utils boost expat openssl
```

### For Fedora (and probably RHEL, CentOS, & Scientific Linux, but untested)

```sh
sudo dnf install @development-tools gcc-c++ libstdc++-static libatomic cmake ccache ninja-build
sudo dnf install alsa-lib-devel avahi-devel boost-devel expat-devel flac-devel libvorbis-devel openssl-devel opus-devel pipewire-jack-audio-connection-kit-devel pulseaudio-libs-devel soxr-devel
```

### For FreeBSD

```sh
sudo pkg install alsa-lib pulseaudio cmake gmake gcc bash avahi libogg libvorbis opus flac libsoxr pkgconfig
```

### For macOS

*Warning:* macOS support is experimental

 1. Install Xcode from the App Store
 2. Install [Homebrew](http://brew.sh)
 3. Install the required libs

```sh
brew install pkgconfig libsoxr expat flac libvorbis boost opus
```

## Build Snapclient and Snapserver

Create a `build` directory in the Snapcast src-root directory (`<snapcast dir>`) and `cd` into it:

```sh
cd <snapcast dir>
mkdir build
cd build
```

Build Snapcast. If you haven't installed boost, but downloaded and extracted the sources, you must point cmake to the boost root directoty, otherwise the part starting with `-DBOOST_ROOT=...` can be omitted.

Other flags that can be passed to `cmake`:

- `-DBUILD_CLIENT=<ON|OFF>`: build the client: yes or no (default `ON`)
- `-DBUILD_SERVER=<ON|OFF>`: build the server: yes or no (default `ON`)
- `-DBUILD_WITH_SSL=<ON|OFF>`: build server and client with TLS support: yes or no (default `ON`)
- `-DBUILD_WITH_FLAC=<ON|OFF>`: build with FLAC support: yes or no (default `ON`)
- `-DBUILD_WITH_VORBIS=<ON|OFF>`: build with VORBIS support: yes or no (default `ON`)
- `-DBUILD_WITH_TREMOR=<ON|OFF>`: build with vorbis using TREMOR: yes or no (default `ON`)
- `-DBUILD_WITH_OPUS=<ON|OFF>`: build with OPUS support: yes or no (default `ON`)
- `-DBUILD_WITH_AVAHI=<ON|OFF>`: build with AVAHI support: yes or no (default `ON`)
- `-DBUILD_WITH_EXPAT=<ON|OFF>`: build with EXPAT support: yes or no (default `ON`)
- `-DBUILD_WITH_PULSE=<ON|OFF>`: build client with PulseAudio support: yes or no (default `OFF`)
- `-DBUILD_WITH_JACK=<ON|OFF>`: build with JACK support: yes or no (default `OFF`)
- `-DBUILD_WITH_PIPEWIRE=<ON|OFF>`: build with PipeWire support: yes or no (default `OFF`)
- `-BUILD_WITH_SDL2=<ON|OFF>`: build with SDL2 support: yes or no (default `OFF`)
- `-BUILD_WITH_SOXR=<ON|OFF>`: build with SOXR resampling support: yes or no (default `ON`)

```sh
cmake .. -DBOOST_ROOT=/path/to/boost_1_8x_0
cmake --build .
```

Binaries will be created in `<snapcast dir>/bin`:

```sh
<snapcast dir>/bin/snapclient
<snapcast dir>/bin/snapserver
```

## Windows (vcpkg)

Prerequisites:

 1. CMake
 2. Visual Studio 2017 or 2019 with C++

Set up [vcpkg](https://github.com/Microsoft/vcpkg)

Install dependencies

```sh
vcpkg.exe install libflac libvorbis soxr opus boost-asio boost-beast --triplet x64-windows
```

Build

```sh
cd <snapcast dir>
mkdir build
cd build && cmake .. -DCMAKE_TOOLCHAIN_FILE=<vcpkg_dir>/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

## Build packages

### Debian packages

Debian packages can be made with the following steps. You can switch pulse audio support on or off by passing `-DBUILD_WITH_PULSE=ON` or `OFF` in the last step:

```sh
sudo apt-get install debhelper python3
cd <snapcast dir>
ln -s extras/package/debian debian
debian/changelog_md2deb.py changelog.md  > debian/changelog
fakeroot make -f debian/rules CMAKEFLAGS="-DBOOST_ROOT=/path/to/boost/boost_1_8x_0 -DCMAKE_BUILD_TYPE:STRING=Release -DBUILD_WITH_PULSE=OFF" binary
```

The resulting debian packages are created in the parent direcory of `<snapcast dir>`

### Gentoo (native)

Snapcast is available under Gentoo's [Portage](https://wiki.gentoo.org/wiki/Portage) package management system. Portage utilises `USE` flags to determine what components are built on compilation. The available options are...

```sh
equery u snapcast
[ Legend : U - final flag setting for installation]
[        : I - package is installed with flag     ]
[ Colors : set, unset                             ]
 * Found these USE flags for media-sound/snapcast-9999:
 U I
 + - avahi       : Build with avahi support
 + + client      : Build and install Snapcast client component
 + - flac        : Build with FLAC compression support
 + + server      : Build and install Snapcast server component
 - - static-libs : Build static libs
 - - tremor      : Build with TREMOR version of vorbis
 + - vorbis      : Build with libvorbis support
```

These can be set either in the [global configuration](https://wiki.gentoo.org/wiki//etc/portage/make.conf#USE) file `/etc/portage/make.conf` or on a per-package basis (as root):

```sh
if [ ! -d "$DIRECTORY" ]; then
    mkdir /etc/portage/package.use/media-sound
fi
echo 'media-sound/snapcast client server flac
```

If for example you only wish to build the server and *not* the client then precede the server `USE` flag with `-` i.e.

```sh
echo 'media-sound/snapcast client -server
```

Once `USE` flags are configured emerge snapcast as root:

```sh
emerge -av snapcast
```

Starting the client or server depends on whether you are using `systemd` or `openrc`. To start using `openrc`:

```sh
/etc/init.d/snapclient start
/etc/init.d/snapserver start
```

To enable the serve and client to start under the default run-level:

```sh
rc-update add snapserver default
rc-update add snapclient default
```

### Android (Cross compile)

Clone [Snapdroid](https://github.com/snapcast/snapdroid), which includes Snapclient as submodule:

```sh
git clone https://github.com/snapcast/snapdroid.git
cd snapdroid
git submodule update --init --recursive
```

and execute `./gradlew build`, which will cross compile Snapclient and bundle it into the Snapdroid App.

### OpenWrt/LEDE (Cross compile)

To cross compile for OpenWrt, please follow the [OpenWrt flavored SnapOS guide](https://github.com/snapcast/snapos/blob/master/openwrt/README.md)

### Buildroot (Cross compile)

To integrate Snapcast into [Buildroot](https://buildroot.org/), please follow the [Buildroot flavored SnapOS guide](https://github.com/snapcast/snapos/blob/master/buildroot-external/README.md)

### webOS (Cross compile)

To cross compile Snapcast client for LG webOS TVs, you need a toolchain for the device's C++ ABI.

webOS apps cannot open the ALSA codec directly because it is owned by the webOS
audio server, and the device's own audio stack is PulseAudio (system mode), so
the sync-accurate setup is the `pulse` player described in
[Deploy and run](#deploy-and-run). When PulseAudio is unavailable or broken on
a device, snapclient can instead be built and run with the **SDL2 player**: the
`libSDL2` shipped on the TV routes SDL audio through that same PulseAudio
mixer, so playback works without any webOS-specific client code. The steps
below build a single binary containing both players.

> **SDL2 is a fallback only: more casting than sync-casting.** SDL2 exposes no
> playback position/latency query, so snapclient has to assume a constant
> latency for it, and the webOS audio stack does not provide one: its
> PulseAudio-based mixer varies its latency at runtime. The result is audible,
> dropout-free playback with degraded multi-room sync: this mode is closer to
> casting than to synchronized casting. Use the `pulse` player for any real
> sync group and fall back to SDL2 only where PulseAudio cannot be used. The
> SDL2 delta is just `-DBUILD_WITH_SDL2=ON` plus `--player sdl2`; see
> [Deploy and run](#deploy-and-run) and [SDL2 fallback](#sdl2-fallback) below.

#### Target platform notes

webOS TVs with ARM SoCs (webOS 3 and later) run a **32-bit armv7 userland with soft-float
calling convention** (`arm-linux-gnueabi`, Debian's `armel` architecture). Newer TVs
("starfish", webOS 5 and later) additionally run a 64-bit kernel and report `aarch64` from
`uname`, but the userland ABI is unchanged: binaries are ELF32, the dynamic linker is
`/lib/ld-linux.so.3` and `.ARM.attributes` lack `Tag_ABI_VFP_args`. An `armhf` (hard-float)
build is incompatible and an `aarch64` build cannot even load. Verify the target over SSH:

```sh
readelf -A /bin/sh   # no "Tag_ABI_VFP_args" => armel (soft-float) is required
```

#### Build Steps (Debian bullseye, tested on webOS 9.2.4)

Debian bullseye ships glibc 2.31, GCC 10, SDL2 2.0.14 and Boost 1.74, so the resulting
binary runs unmodified on webOS 5 to 9: those TVs ship glibc >= 2.31 and already provide
`libSDL2-2.0.so.0`, `libasound.so.2`, `libFLAC.so.8`, `libogg.so.0`, `libvorbis.so.0` and
`libopus.so.0` in `/usr/lib` (link `libstdc++` statically to stay independent of the
device's `libstdc++` version). Debian publishes no armel container image, so run the
armel rootfs from `multiarch/debian-debootstrap` under qemu:

```sh
# register qemu for ARM containers (once per host)
docker run --privileged --rm tonistiigi/binfmt --install arm

docker run --rm -v "$PWD":/src:ro multiarch/debian-debootstrap:armel-bullseye bash
```

Inside the container (bullseye moved to `archive.debian.org`):

```sh
printf 'deb http://archive.debian.org/debian bullseye main\n' > /etc/apt/sources.list
apt-get -o Acquire::Check-Valid-Until=false update
apt-get install -y --no-install-recommends build-essential cmake ninja-build pkg-config \
    libboost-dev libsdl2-dev libpulse-dev libasound2-dev libflac-dev libogg-dev libvorbis-dev \
    libopus-dev libexpat1-dev libsoxr-dev

cp -a /src /work && cd /work
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="-march=armv7-a -mfpu=vfpv3-d16 -mfloat-abi=softfp" \
    -DCMAKE_CXX_FLAGS="-march=armv7-a -mfpu=vfpv3-d16 -mfloat-abi=softfp" \
    -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc" \
    -DBUILD_WITH_SDL2=ON \
    -DBUILD_WITH_PULSE=ON \
    -DBUILD_SERVER=OFF \
    -DBUILD_CLIENT=ON \
    -DBUILD_WITH_ALSA=OFF \
    -DBUILD_WITH_PIPEWIRE=OFF
cmake --build build
```

The binary is written to `bin/snapclient`.

`libsoxr-dev` is auto-detected by CMake and enables the soxr resampler, which the
client uses to lock its audio clock to the server and absorb clock drift (without
it snapclient logs `Soxr not available, resampling not supported` and will slowly
drift out of sync). Debian ships only a shared soxr, so copy `libsoxr.so.1*` from
the container's `/usr/lib/*/` next to the binary and start the client with
`LD_LIBRARY_PATH=/media/internal/downloads` if the TV has no libsoxr of its own.

#### Deploy and run

Root access via [RootMy.TV](https://rootmy.tv) or the
[webosbrew](https://github.com/webosbrew) tooling. `/media/internal` survives reboots.

Use the `pulse` player: webOS mixes audio through its system PulseAudio
instance, and its socket path is model specific; on webOS 9.2.4 it is
`/tmp/var/run/pulse/native` (check with `ls /tmp/var/run/pulse /run/pulse
/tmp/pulse`):

```sh
scp bin/snapclient root@<tv-ip>:/media/internal/
ssh root@<tv-ip> 'chmod +x /media/internal/snapclient \
    && PULSE_SERVER=unix:/tmp/var/run/pulse/native \
       /media/internal/snapclient tcp://<server-ip>:1704 --player pulse'
```

#### SDL2 fallback

When PulseAudio is unavailable or broken on the device (no server socket to
connect to, or a non-working one), run the very same binary with the SDL2
player instead: the build above already contains both players, so the only
delta is to replace `--player pulse` with `--player sdl2`:

```sh
ssh root@<tv-ip> '/media/internal/snapclient tcp://<server-ip>:1704 --player sdl2'
```

Keep a `PULSE_SERVER=unix:<path>` prefix if the pulse player needed one: the
`libSDL2` shipped on the TV routes SDL audio via PulseAudio too. For a minimal
fallback-only build, swap `-DBUILD_WITH_PULSE=ON` for `-DBUILD_WITH_SDL2=ON` in
the configure step; everything else, including the soxr notes above, applies
unchanged.

Keep the warning at the head of this section in mind: since SDL2 cannot report
the playback position, `--latency <ms>` can only hide a constant offset, not
track a varying one, so the client behaves more like a cast receiver than a
member of a sync group.

#### Latency

Measured on webOS 9.2.4, the acoustic output of the pulse player lags a desktop
reference client by roughly 85-95 ms. `--latency <ms>` shifts playback earlier by
1 ms per 1 ms set (verified by recording both speakers and cross-correlating a
click test signal), so a positive value compensates a late device and brings the
TV into sync with the rest of the group. The value must be set at client startup:
changing the latency of an already-playing client can starve its buffer
(silence) or destabilize it, so restart the client instead.

Which audio players work on webOS:

- `pulse`: the only player with real playback-latency feedback on webOS, and it
  follows the system audio policy (routing, ducking, `media.role=music`)
- `sdl2`: fallback only (see [SDL2 fallback](#sdl2-fallback) above): works
  because the `libSDL2` shipped on the TV routes audio via PulseAudio, but SDL2
  exposes no playback position/latency API, so snapclient has to assume a
  constant latency that the webOS mixer does not actually provide; timing is
  noticeably less stable than with the pulse player, closer to casting than to
  synchronized casting
- `alsa`: PCM devices are listed (`sysdefault:CARD=...`) but playback fails
  with `XRUN`/`Broken pipe`, because the codec is owned by the webOS audio
  server; do not use

#### Build Steps (older TVs, openlgtv toolchain)

For pre-starfish TVs (webOS 3.x/4.x), the
[openlgtv buildroot toolchain](https://github.com/openlgtv/buildroot-nc4) provides a
matching `arm-webos-linux-gnueabi` sysroot and can be used with
`-DCMAKE_TOOLCHAIN_FILE=<toolchain>/toolchain.cmake` and the same CMake options as above.
