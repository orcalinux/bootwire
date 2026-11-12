#!/bin/sh
# Build dist/bootwire_<version>_all.deb from the sources under desktop/.
#
# The package uses the system Python and Debian's own packages for every
# dependency, so nothing is downloaded and no virtual environment is shipped.
# The CLI dependencies are hard dependencies; the Qt packages the desktop
# application needs are Recommends, so a headless machine can install the CLI
# alone with `apt install --no-install-recommends`.
#
# Needs: dpkg-deb, fakeroot, gzip. Run from anywhere: packaging/build-deb.sh
#
# The Maintainer field comes from $DEB_MAINTAINER ("Name <email>"), or from
# `git config user.name` and `user.email` when that is not set.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
src="$root/desktop"
out="$root/dist"

version=$(sed -n 's/^version = "\(.*\)"$/\1/p' "$src/pyproject.toml")
[ -n "$version" ] || { echo "build-deb: no version in desktop/pyproject.toml" >&2; exit 1; }

maintainer=${DEB_MAINTAINER:-}
if [ -z "$maintainer" ]; then
    name=$(git -C "$root" config user.name || true)
    email=$(git -C "$root" config user.email || true)
    if [ -z "$name" ] || [ -z "$email" ]; then
        echo 'build-deb: set DEB_MAINTAINER="Name <email>" (git user.name/user.email are not set)' >&2
        exit 1
    fi
    maintainer="$name <$email>"
fi

for tool in dpkg-deb fakeroot gzip; do
    command -v "$tool" >/dev/null || { echo "build-deb: $tool is not installed" >&2; exit 1; }
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
pkg="$stage/bootwire"
py="$pkg/usr/lib/python3/dist-packages"
doc="$pkg/usr/share/doc/bootwire"

mkdir -p "$pkg/DEBIAN" "$py" "$pkg/usr/bin" "$pkg/usr/share/man/man1" \
    "$pkg/usr/share/applications" "$pkg/usr/share/icons/hicolor/scalable/apps" \
    "$pkg/usr/share/icons/hicolor/256x256/apps" "$doc/examples"

# Python packages, without caches. Bytecode is compiled on the target system.
for package in bootwire bootwire_cli bootwire_gui; do
    cp -r "$src/src/$package" "$py/"
done
find "$py" -name __pycache__ -type d -prune -exec rm -rf {} +
find "$py" -name '*.py[co]' -delete

# pip metadata, so `pip list` and importlib.metadata know the package.
info="$py/bootwire-$version.dist-info"
mkdir -p "$info"
cat > "$info/METADATA" <<EOF
Metadata-Version: 2.1
Name: bootwire
Version: $version
Summary: Host-side library and CLI for the BootWire Protocol bootloader
License: MIT
Requires-Python: >=3.9
EOF
echo "dpkg" > "$info/INSTALLER"

cat > "$pkg/usr/bin/bootwire" <<'EOF'
#!/usr/bin/python3
from bootwire_cli.main import app

if __name__ == "__main__":
    app(prog_name="bootwire")
EOF
cat > "$pkg/usr/bin/bootwire-gui" <<'EOF'
#!/usr/bin/python3
import sys

from bootwire_gui.main import main

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 755 "$pkg/usr/bin/bootwire" "$pkg/usr/bin/bootwire-gui"

gzip -9n -c "$src/man/bootwire.1" > "$pkg/usr/share/man/man1/bootwire.1.gz"
gzip -9n -c "$src/man/bootwire-gui.1" > "$pkg/usr/share/man/man1/bootwire-gui.1.gz"

assets="$src/src/bootwire_gui/assets"
cp "$assets/bootwire.desktop" "$pkg/usr/share/applications/bootwire.desktop"
cp "$assets/bootwire.svg" "$pkg/usr/share/icons/hicolor/scalable/apps/bootwire.svg"
cp "$assets/bootwire.png" "$pkg/usr/share/icons/hicolor/256x256/apps/bootwire.png"

cp "$src/bootwire.yaml" "$doc/examples/bootwire.yaml"
cp "$root/README.md" "$doc/README.md"
cat > "$doc/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: bootwire

Files: *
Copyright: Mahmoud Abdelraouf
License: Expat
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
EOF
cat > "$stage/changelog" <<EOF
bootwire ($version) unstable; urgency=low

  * Local build of BootWire $version.

 -- $maintainer  $(date -R)
EOF
gzip -9n -c "$stage/changelog" > "$doc/changelog.gz"

size=$(du -sk "$pkg/usr" | cut -f1)
cat > "$pkg/DEBIAN/control" <<EOF
Package: bootwire
Version: $version
Section: electronics
Priority: optional
Architecture: all
Maintainer: $maintainer
Installed-Size: $size
Depends: python3 (>= 3.9), python3-serial (>= 3.5), python3-typer (>= 0.9), python3-rich (>= 13), python3-yaml (>= 6)
Recommends: python3-pyside6.qtcore (>= 6.8), python3-pyside6.qtgui, python3-pyside6.qtqml, python3-pyside6.qtquick, python3-pyside6.qtquickcontrols2, qml6-module-qtquick, qml6-module-qtquick-controls, qml6-module-qtquick-layouts, qml6-module-qtquick-dialogs, qml6-module-qtquick-templates, qml6-module-qtquick-window, qml6-module-qtqml-workerscript, python3-pyte, python3-ptyprocess
Description: firmware updates for Cortex-M bootloaders over UART
 BootWire is a small stop-and-wait protocol for updating the firmware of a
 32-bit ARM Cortex-M microcontroller over UART and for sending user-defined
 commands to its bootloader.
 .
 This package provides the bootwire command-line tool, the Python library it
 is built on, a simulated target for working without hardware, and the
 bootwire-gui desktop application. The desktop application needs the
 recommended Qt packages; the command-line tool does not.
EOF

cat > "$pkg/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && command -v py3compile >/dev/null 2>&1; then
    py3compile -p bootwire || true
fi
EOF
cat > "$pkg/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
if command -v py3clean >/dev/null 2>&1; then
    py3clean -p bootwire || true
fi
find /usr/lib/python3/dist-packages/bootwire /usr/lib/python3/dist-packages/bootwire_cli \
    /usr/lib/python3/dist-packages/bootwire_gui -name __pycache__ -type d -prune \
    -exec rm -rf {} + 2>/dev/null || true
EOF
chmod 755 "$pkg/DEBIAN/postinst" "$pkg/DEBIAN/prerm"

find "$pkg" -type d -exec chmod 755 {} +
find "$pkg/usr/lib" "$pkg/usr/share" -type f -exec chmod 644 {} +
(cd "$pkg" && find usr -type f -exec md5sum {} + > DEBIAN/md5sums)

mkdir -p "$out"
deb="$out/bootwire_${version}_all.deb"
fakeroot dpkg-deb --build --root-owner-group "$pkg" "$deb" >/dev/null
echo "built: $deb"
