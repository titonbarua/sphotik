#!/usr/bin/env python3
import sys
import shutil
import os.path
import subprocess

ibus_component_bank = "/usr/share/ibus/component/"

python_path = sys.executable
source_dir = os.path.realpath(os.path.dirname(__file__))
engine_path = os.path.join(source_dir, "ibus_sphotik.py")
engine_command = "'{}' '{}' --ibus".format(python_path, engine_path)

# Check for python version.
if not sys.version_info >= (3, 4):
    print(
        "Python version 3.4 or higher is required to run sphotik."
        "\nIn Ubuntu/Debian, install or upgrade python3 with this"
        "\ncommand:\n\tapt-get install python3")
    sys.exit(1)

# Check if ibus is installed ( in a silly way ).
if not os.path.isdir(ibus_component_bank):
    print(
        "Either IBus is not installed, or installed to non-standard"
        "\nlocation. If it is not installed, you can install with"
        "\nthis command (in Ubuntu/Debian):"
        "\n\tapt-get install ibus ibus-gtk ibus-gtk3 im-config")
    sys.exit(2)

# Let's try to import required gobject introspection repositories.
try:
    from gi.repository import IBus, GLib
except ImportError:
    print(
        "Required gobject introspection repositories are not found."
        "\nIn Ubuntu/Debian, try to install them with this command:"
        "\n\tapt-get install python3-gi gir1.2-glib-2.0 gir1.2-ibus-1.0")
    sys.exit(3)

# Time for manual file installation ...
#--------------------------------------------------------------------\
files_manually_installed = []

# Install ibus component description file for sphotik.
from sphotik.engine import render_component_template
try:
    version_file = os.path.join(os.path.dirname(__file__), "VERSION.txt")
    with open(version_file) as f:
        version = f.read().strip()

    component_file = os.path.join(ibus_component_bank, "sphotik.xml")
    with open(component_file, "w") as f:
        f.write(render_component_template(
            version = version,
            run_path = engine_command,
            setup_path = '',
            icon_path = '',
        ))

    os.chmod(component_file, 0o755)
    files_manually_installed.append(component_file)
except Exception as e:
    print("Failed to install ibus component file: {}".format(e))
    sys.exit(8)
#--------------------------------------------------------------------/

# Comfort the user, for she has jumped through such long hoops
# with hopes of using this program! :V
print("Installation successful!")

# Write uninstaller file.
#-------------------------------------------------------------------\
UNINSTALLER_TEMPLATE = """\
#!/bin/sh
{file_removal_commands}
"""

uninstaller_path = os.path.join(source_dir,"uninstaller.sh")
with open(uninstaller_path, 'w') as f:
    f.write(UNINSTALLER_TEMPLATE.format(
        file_removal_commands = "\n".join([
            "rm -v '{}'".format(x) for x in files_manually_installed]),
    ))

os.chmod(uninstaller_path, 0o777)
#-------------------------------------------------------------------/
print("Created uninstaller: {}".format(uninstaller_path))
