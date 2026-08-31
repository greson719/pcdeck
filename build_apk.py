"""
Build Script for PCDeck Pro Android APK (.apk)
Uses local Android SDK build-tools and JDK 17 to produce a signed, aligned APK.
"""

import os
import subprocess
import sys
import zipfile
import shutil

ANDROID_SDK = r"C:\Android"
BUILD_TOOLS_VER = "36.0.0"
PLATFORM_VER = "android-36"

AAPT2 = os.path.join(ANDROID_SDK, "build-tools", BUILD_TOOLS_VER, "aapt2.exe")
D8 = os.path.join(ANDROID_SDK, "build-tools", BUILD_TOOLS_VER, "d8.bat")
ZIPALIGN = os.path.join(ANDROID_SDK, "build-tools", BUILD_TOOLS_VER, "zipalign.exe")
APKSIGNER = os.path.join(ANDROID_SDK, "build-tools", BUILD_TOOLS_VER, "apksigner.bat")
ANDROID_JAR = os.path.join(ANDROID_SDK, "platforms", PLATFORM_VER, "android.jar")

BUILD_DIR = "build_android"
OUTPUT_APK = "PCDeck.apk"
KEYSTORE = "pcdeck_release.keystore"


def run(cmd, desc=""):
    print(f"\n[+] {desc}...")
    print(f"    Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] ERROR: {res.stderr}")
        print(f"[-] STDOUT: {res.stdout}")
        sys.exit(1)
    else:
        if res.stdout.strip():
            print(f"    Output: {res.stdout.strip()[:200]}")
    return res


def main():
    print("=======================================================")
    print("         [+] BUILDING PCDECK ANDROID APK (.APK)")
    print("=======================================================")

    # Sync web assets from static/ into android_app/assets/
    print("\n[+] Syncing static assets into android_app/assets/...")
    os.makedirs("android_app/assets", exist_ok=True)
    ignore_exts = {".apk", ".exe", ".zip", ".aab", ".idsig", ".msix"}
    for fname in os.listdir("static"):
        if any(fname.lower().endswith(ext) for ext in ignore_exts):
            continue
        src = os.path.join("static", fname)
        dst = os.path.join("android_app/assets", fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
    print("    OK: Static assets synced without binary artifacts.")

    # Ensure build directories exist
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "gen"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "obj"), exist_ok=True)

    # 1. Compile resources with aapt2
    run(
        f'"{AAPT2}" compile --dir android_app/res -o "{BUILD_DIR}/res.zip"',
        "Compiling Android Resources"
    )

    # 2. Link resources and generate R.java
    run(
        f'"{AAPT2}" link -o "{BUILD_DIR}/unaligned.apk" -I "{ANDROID_JAR}" --manifest android_app/AndroidManifest.xml -A android_app/assets --java "{BUILD_DIR}/gen" "{BUILD_DIR}/res.zip" --min-sdk-version 21 --target-sdk-version 36 --auto-add-overlay',
        "Linking Resources & Generating R.java"
    )

    # 3. Find and compile all Java sources (R.java, MainActivity.java, NeonTrackAccessibilityService.java)
    java_files = []
    for root, _, files in os.walk("android_app/src"):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))
    for root, _, files in os.walk(os.path.join(BUILD_DIR, "gen")):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(root, f))

    java_files_str = " ".join(f'"{f}"' for f in java_files)

    # 4. Compile Java sources
    run(
        f'javac -encoding UTF-8 -cp "{ANDROID_JAR}" -d "{BUILD_DIR}/obj" {java_files_str}',
        "Compiling Java Source Files"
    )

    # 5. Compile bytecode to Dalvik Executable (classes.dex)
    class_files = []
    for root, _, files in os.walk(os.path.join(BUILD_DIR, "obj")):
        for f in files:
            if f.endswith(".class"):
                class_files.append(os.path.join(root, f))

    class_files_str = " ".join(f'"{f}"' for f in class_files)
    run(
        f'"{D8}" --output "{BUILD_DIR}" {class_files_str}',
        "Converting to DEX format (d8)"
    )

    # 6. Add classes.dex into unaligned.apk
    print("\n[+] Adding classes.dex to APK package...")
    dex_path = os.path.join(BUILD_DIR, "classes.dex")
    apk_path = os.path.join(BUILD_DIR, "unaligned.apk")

    # Append classes.dex using zipfile
    with zipfile.ZipFile(apk_path, "a", compression=zipfile.ZIP_DEFLATED) as apk_zip:
        apk_zip.write(dex_path, "classes.dex")
    print("    OK: classes.dex embedded into APK")

    # 7. Zipalign the APK
    aligned_apk = os.path.join(BUILD_DIR, "aligned.apk")
    run(
        f'"{ZIPALIGN}" -p -f -v 4 "{apk_path}" "{aligned_apk}"',
        "Aligning APK (zipalign 4-byte boundaries)"
    )

    # 8. Create release keystore if not exists
    if not os.path.exists(KEYSTORE):
        run(
            f'keytool -genkey -v -keystore "{KEYSTORE}" -alias pcdeckkey -keyalg RSA -keysize 2048 -validity 10000 -storepass pcdeck2026 -keypass pcdeck2026 -dname "CN=PCDeck Pro,OU=Tools,O=PCDeck,C=US"',
            "Creating Release Signing Keystore"
        )

    # 9. Sign APK with apksigner (v1, v2, v3 schemes)
    run(
        f'"{APKSIGNER}" sign --ks "{KEYSTORE}" --ks-pass pass:pcdeck2026 --ks-key-alias pcdeckkey --key-pass pass:pcdeck2026 --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true --out "{OUTPUT_APK}" "{aligned_apk}"',
        "Signing APK (apksigner)"
    )

    if os.path.exists(OUTPUT_APK):
        size_kb = os.path.getsize(OUTPUT_APK) / 1024
        print("\n" + "=" * 55)
        print(f"OK: SUCCESS: Android APK generated at '{OUTPUT_APK}' ({size_kb:.1f} KB)")
        print("=======================================================\n")
    else:
        print("[-] Failed to generate APK.")


if __name__ == "__main__":
    main()
