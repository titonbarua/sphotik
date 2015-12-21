#!/usr/bin/env python3
import sys
import shutil
import os.path
import subprocess

INSTALLATION_PATH = "/opt/sphotik/"
IBUS_COMPONENT_BANK = "/usr/share/ibus/component/"

MANIFEST_FILENAME = "MANIFEST.in"
ENGINE_FILENAME = "ibus_sphotik.py"
IBUS_COMPONENT_FILENAME = "sphotik.xml"
UNINSTALLER_FILENAME = "uninstaller.sh"
VERSION_FILENAME = "VERSION.txt"

INSTALLED_FILE_OWNER = 0
INSTALLED_FILE_GROUP = 0
INSTALLED_FILE_MODE = 0o755

python_path = sys.executable

source_dir = os.path.realpath(os.path.dirname(__file__))
version_path = os.path.join(source_dir, VERSION_FILENAME)
manifest_path = os.path.join(source_dir, MANIFEST_FILENAME)

install_dir = INSTALLATION_PATH
installed_engine_path = os.path.join(install_dir, ENGINE_FILENAME)
installed_engine_command = "'{}' '{}' --ibus".format(
    python_path, installed_engine_path)
installed_ibus_component_path = os.path.join(
    IBUS_COMPONENT_BANK, IBUS_COMPONENT_FILENAME)
installed_uninstaller_path = os.path.join(install_dir, UNINSTALLER_FILENAME)

# Check for python version.
if not sys.version_info >= (3, 4):
    user_help = """
[ ERROR ] Python version 3.4 or higher is required to run Sphotik. Install
python3.4 or higher using your distributions package management command:
    [ Ubuntu/Debian ]
        apt-get install python3
"""
    print(user_help.strip())
    sys.exit(1)

# Check if ibus is installed ( in a silly way ).
if not os.path.isdir(IBUS_COMPONENT_BANK):
    user_help = """
[ ERROR ] Either IBus is not installed, or installed in non-standard location.
For the first case, install IBus using system package manager:
    [ Ubuntu/Debian ]
        apt-get install ibus ibus-gtk ibus-gtk3 im-config

For the second case, edit the installer script and setup "IBUS_COMPONENT_BANK"
variable according to your IBus installation.
"""
    print(user_help.strip())
    sys.exit(2)


# Let's try to import required gobject introspection repositories.
try:
    from gi.repository import IBus, GLib
except (ImportError, AttributeError):
    user_help = """
[ ERROR ] Required "GObject Introspection" repositories are not found.
Install them with system package manager:
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
    # This is just an warning. Installation will continue even if
    # this step fails.
    user_help = """
[ WARNING ] Either enchant binding for python3 is not available or
no bangla dictionary was found. Without both of them, dictionary
suggestions will not be available. You may install them with
system package manager:
    [ Ubuntu/Debian ]
        apt-get install python3-enchant
        apt-get install hunspell-bn
"""
    print(user_help.strip())

# Try to uninstall an existing installation.
if os.path.isfile(installed_uninstaller_path):
    print("Trying to uninstall existing installation ...")
    subprocess.check_call([installed_uninstaller_path])


# Real installation begins ...
#--------------------------------------------------------------------\
files_installed = []

# Copy source files to installation path.
try:
    with open(manifest_path) as f:
        for fname in f:
            fname = fname.strip()
            if not fname:
                continue

            src = os.path.join(source_dir, fname)
            dst = os.path.join(install_dir, fname)

            dstdir = os.path.dirname(dst)
            if not os.path.isdir(dstdir):
                os.makedirs(dstdir, INSTALLED_FILE_MODE)

            shutil.copyfile(src, dst, follow_symlinks=False)
            os.chown(dst, INSTALLED_FILE_OWNER, INSTALLED_FILE_GROUP)
            os.chmod(dst, INSTALLED_FILE_MODE)

            files_installed.append(dst)
            print("Installed '{}'".format(dst))

except Exception as e:
    print("[ ERROR ] Failed to install source files: {}".format(e))
    sys.exit(5)

# Install ibus component description file for sphotik.
from sphotik.engine import render_component_template
try:
    with open(version_path) as f:
        version = f.read().strip()

    with open(installed_ibus_component_path, "w") as f:
        f.write(render_component_template(
            version=version,
            run_path=installed_engine_command,
            setup_path='',
            icon_path='',
        ))

    os.chmod(installed_ibus_component_path, 0o644)
    files_installed.append(installed_ibus_component_path)
except Exception as e:
    print("[ ERROR ] Failed to install ibus component file: {}".format(e))
    sys.exit(6)
#--------------------------------------------------------------------/

# Comfort the user, for she has jumped through such long hoops
# with hopes of using this program! :V
print("=" * 50 + "\nInstallation successful!\n" + "=" * 50)
print("** Sphotik installed to: {} **".format(install_dir))

# Write uninstaller file.
#-------------------------------------------------------------------\
UNINSTALLER_TEMPLATE = """\
#!/bin/sh
{file_removal_commands}
"""

with open(installed_uninstaller_path, 'w') as f:
    f.write(UNINSTALLER_TEMPLATE.format(
        file_removal_commands="\n".join([
            "if [ -f '{0}' ] ; then rm -v '{0}' ; fi"
            .format(x) for x in files_installed]),
    ))

os.chown(
    installed_uninstaller_path,
    INSTALLED_FILE_OWNER,
    INSTALLED_FILE_GROUP)
os.chmod(installed_uninstaller_path, 0o755)
#-------------------------------------------------------------------/
print("Created uninstaller: {}".format(installed_uninstaller_path))
