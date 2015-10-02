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
    user_help = """
Python version 3.4 or higher is required to run Sphotik. Install python3.4
or higher using your distributions package management command:
    [ Ubuntu/Debian ]
        apt-get install python3
"""
    print(user_help.strip())
    sys.exit(1)

# Check if ibus is installed ( in a silly way ).
if not os.path.isdir(ibus_component_bank):
    user_help = """
Either IBus is not installed, or installed in non-standard location.
For the first case, install IBus using system package manager:
    [ Ubuntu/Debian ]
        apt-get install ibus ibus-gtk ibus-gtk3 im-config

For the second case, edit the installer script and setup "ibus_component_bank"
variable according to your IBus installation.
"""
    print(user_help.strip())
    sys.exit(2)

# Let's try to import required gobject introspection repositories.
try:
    from gi.repository import IBus, GLib
except (ImportError, AttributeError):
    user_help = """
Required "GObject Introspection" repositories are not found. Install them
with system package manager:
    [ Ubuntu/Debian ]
        apt-get install python3-gi gir1.2-glib-2.0 gir1.2-ibus-1.0
"""
    print(user_help.strip())
    sys.exit(3)


# Try to open a bangla dictionary with the help of enchant.
try:
    import enchant
    from enchant.errors import DictNotFoundError

    enchant_dicts_to_try = ['bn_BD', 'bn']
    for dname in enchant_dicts_to_try:
        try:
            d = enchant.Dict('bn_BD')
            break
        except DictNotFoundError:
            pass
    else:
        raise RuntimeError("Didn't find any expected dictionary.")

except (ImportError, RuntimeError):
    # Not suggesting aspell-bn, since I can't get it working.
    user_help = """
Required "Enchant" binding for python3 is not found. Install it with
system package manager:
    [ Ubuntu/Debian ]
        apt-get install python3-enchant hunspell-bn
"""
    print(user_help.strip())
    sys.exit(4)

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
    sys.exit(5)
#--------------------------------------------------------------------/

# Comfort the user, for she has jumped through such long hoops
# with hopes of using this program! :V
print("Installation successful!")
print("** DO NOT REMOVE THIS DIRECTORY: {} **".format(source_dir))

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
