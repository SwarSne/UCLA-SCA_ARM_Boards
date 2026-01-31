Desktop/merged_test_sneha.py
import subprocess
import os
import sys
import shutil
import time
import pyvisa
import numpy as np

############################
# PATH CONFIGURATION
############################

BASE_DIR = "/home/sysarch/Desktop/nrfstuff"
WEST_WS = "west_workspace"
APP_PATH = "zephyr/samples/basic/fade_led"
BOARD = "nrf52dk/nrf52832"
ACTION = "flash"
# Folder containing sample1.c, sample2.c...
SAMPLES_DIR = "/home/sysarch/Desktop/nrfstuff/west_workspace/zephyr/samples/basic/fade_led/src/"

#  THIS is the important target main.c
TARGET_MAIN = "/home/sysarch/Desktop/nrfstuff/west_workspace/zephyr/samples/basic/fade_led/src/main.c"

OUTPUT_DIR = "/home/sysarch/Desktop/traces"
os.makedirs(OUTPUT_DIR, exist_ok=True)

############################
# OSCILLOSCOPE CONFIG
############################

SCOPE_RESOURCE = "USB0::0x0957::0x1781::MY61500133::0::INSTR"
VISA_LIB = "/opt/keysight/iolibs/libktvisa32.so"

rm = pyvisa.ResourceManager(VISA_LIB)
scope = rm.open_resource(SCOPE_RESOURCE)
scope.timeout = None

############################
# FLASH FUNCTION
############################

############################
# FLASH FUNCTION
############################

def flash_firmware():
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
        raise RuntimeError("Flashing failed")

############################
# OSCILLOSCOPE FUNCTION
############################

def capture_trace(name):

    print(f"📡 Capturing trace for {name}")
    ################################
    # Reset + Setup
    ################################

    scope.timeout = None

    scope.clear()
    scope.write("*CLS")
    scope.write("*RST")

    scope.write(":SINGle")

    # Channel configuration
    scope.write(":CHAN1:SCAL 2")
    scope.write(":CHAN1:OFFS -365e-3")
    scope.write(":CHAN2:SCAL 0.010")
    scope.write(":CHAN2:OFFS 21.75e-3")
    scope.write(":CHAN1:DISPlay ON")
    scope.write(":CHAN2:DISPlay ON")

    ################################
    # Trigger configuration
    ################################

    scope.write(":TRIGger:EDGE:SOURCe CHAN1")
    scope.write(":TRIGger:EDGE:STATE RISing")
    scope.write(":TRIGger:EDGE:LEVel 1.78")
    scope.write(":TRIGger:EDGE:COUPling DC")
    scope.write(":TRIGger:MODE NORMAL")

    scope.write(":TRIG:MODE Edge")
    scope.write(":TRIG:EDGE:SOURcE CHANnel1")
    scope.write(":TRIG:EDGE:SLOP POS")
    scope.write(":TRIG:LEV 1.78")

    ################################
    # Timebase
    ################################

    scope.write(":TIM:SCAL 70e-6")
    scope.write(":TIMebase:POSition -1e-6")
    _ = scope.query("TIMebase:POSition?")  # forced sync
    scope.write(":ACQ:TYPE HRES")
# Channel 2 waveform config
    ################################

    scope.write(":WAVeform:SOURce CHANnel2")
    scope.write(":WAVeform:FORMat ASCii")

    ################################
    # Wait for trigger
    ################################

    scope.timeout = 1000

    scope.write(":TRIGger:EDGE:SOURCe?")
    s = scope.read_raw()
    print(s)

    while True:
        scope.write("*OPC?")
        p = scope.read_raw()

        if p:
            print("Triggered")
            break

    ################################
    # CHANNEL 1
    ################################

    scope.write(":WAV:SOUR CHAN1")
    scope.write(":WAV:FORM BYTE")
    scope.write(":WAV:MODE RAW")

    raw = scope.query_binary_values(
        ":WAV:DATA?",
        datatype="B",
        container=np.array
    )

    yinc = float(scope.query(":WAV:YINC?"))
    yor  = float(scope.query(":WAV:YOR?"))
    yref = float(scope.query(":WAV:YREF?"))

    c1 = (raw - yref) * yinc + yor

    c1_file = os.path.join(OUTPUT_DIR, f"{name}_c1.txt")

    with open(c1_file, "w") as f:
        for i in c1:
            f.write(str(i) + "\n")

    ################################
    # CHANNEL 2
    ################################

    scope.write(":WAV:SOUR CHAN2")
    scope.write(":WAV:FORM BYTE")
    scope.write(":WAV:MODE RAW")

    raw = scope.query_binary_values(
        ":WAV:DATA?",
        datatype="B",
        container=np.array
    )

    yinc = float(scope.query(":WAV:YINC?"))
    yor  = float(scope.query(":WAV:YOR?"))
    yref = float(scope.query(":WAV:YREF?"))

    c2 = (raw - yref) * yinc + yor

    c2_file = os.path.join(OUTPUT_DIR, f"{name}_c2.txt")

    with open(c2_file, "w") as f:
        for i in c2:
            f.write(str(i) + "\n")

    print(f"Saved {name}")

def run_experiment():

    sample_files = sorted(f for f in os.listdir(SAMPLES_DIR) if f.endswith(".c"))

    print(f"Found {len(sample_files)} samples")

    for sample in sample_files:
        if sample == "main.c":
            continue

        sample_path = os.path.join(SAMPLES_DIR, sample)
        sample_name = os.path.splitext(sample)[0]

        print("\n==============================")
        print(f"Running {sample_name}")
       print("==============================")

        #  Copy into blinky/main.c
        shutil.copy(sample_path, TARGET_MAIN)

        print("Copied firmware → main.c")

        # Flash board
        flash_firmware()

        # Let MCU boot
        time.sleep(1)

        # Capture trace
        capture_trace(sample_name)

    print("\n Experiment complete!")


if __name__ == "__main__":
    run_experiment()
    rm.close()
                                                              253,14        Bot







