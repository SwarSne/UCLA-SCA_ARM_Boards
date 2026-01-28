import subprocess
import os
import sys

BASE_DIR = os.path.expanduser("~/Desktop/nrfstuff")
WEST_WS = "west_workspace"
APP_PATH = "zephyr/samples/basic/fade_led"
BOARD = "nrf52dk/nrf52832"
ACTION = "flash"

# adjust version if needed
# ZEPHYR_ENV = os.path.expanduser("~/Desktop/nrfstuff/west_workspace/zephyr/zephyr-env.sh")

bash_script = f"""
set -e

echo "=== Launching nRF Toolchain ==="
cd "{BASE_DIR}"
./nrfutil toolchain-manager launch --shell << 'EOF'
cd "{WEST_WS}"
source zephyr/zephyr-env.sh

cd "{APP_PATH}"

echo "=== Cleaning build directory ==="
rm -rf build

echo "=== Building for board: {BOARD} ==="
west build -b {BOARD}

if [ "{ACTION}" = "flash" ]; then
    echo "=== Flashing device ==="
    west flash
elif [ "{ACTION}" = "erase" ]; then
    echo "=== Erasing device ==="
    west flash --erase
else
    echo "=== Build only ==="
fi

EOF
"""


result = subprocess.run(
    ["bash", "-c", bash_script],
    text=True
)

if result.returncode != 0:
    sys.exit(result.returncode)
