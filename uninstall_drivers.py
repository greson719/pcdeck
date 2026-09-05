import ctypes
import os
import sys
import time

DRIVERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers")

def uninstall():
    dll64 = os.path.join(DRIVERS_DIR, "UnityCaptureFilter64.dll")
    dll32 = os.path.join(DRIVERS_DIR, "UnityCaptureFilter32.dll")
    exe64 = os.path.join(DRIVERS_DIR, "VBCABLE_Setup_x64.exe")

    print("=======================================================")
    print("      PCDECK DRIVER UNINSTALLATION UTILITY")
    print("=======================================================")
    
    # 1. Unregister webcam DirectShow filter
    print("[1] Requesting UAC to unregister UnityCapture webcam...")
    args = f'/u /s "{dll64}"'
    if os.path.exists(dll32):
        args += f' /u /s "{dll32}"'
    ret_cam = ctypes.windll.shell32.ShellExecuteW(None, "runas", "regsvr32.exe", args, None, 1)
    print(f"    Webcam unregister trigger result: {ret_cam}")

    time.sleep(1.5)

    # 2. Uninstall VB-Audio Virtual Cable
    print("\n[2] Requesting UAC to uninstall VB-Audio Virtual Cable...")
    if os.path.exists(exe64):
        ret_mic = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe64, "-u -h", DRIVERS_DIR, 1)
    # 3. Uninstall ViGEmBus Virtual Gamepad Driver
    print("\n[3] Requesting UAC to uninstall ViGEmBus Virtual Gamepad Driver...")
    exe_vigem = os.path.join(DRIVERS_DIR, "ViGEmBus_Setup.exe")
    if os.path.exists(exe_vigem):
        ret_gp = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_vigem, "/uninstall /quiet", DRIVERS_DIR, 1)
        print(f"    ViGEmBus uninstall trigger result: {ret_gp}")
    else:
        print("    ViGEmBus_Setup.exe not found.")

    print("\n[+] Please click 'Yes' on any Windows UAC prompts on your screen.")

if __name__ == "__main__":
    uninstall()
