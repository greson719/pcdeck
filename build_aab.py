import os
import sys
import shutil
import zipfile
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(ROOT, "build_android")
OBJ_DIR = os.path.join(BUILD_DIR, "obj")
GEN_DIR = os.path.join(BUILD_DIR, "gen")
DEX_DIR = os.path.join(BUILD_DIR, "dex")
MODULE_DIR = os.path.join(BUILD_DIR, "base_module")
TOOLS_DIR = os.path.join(ROOT, "tools")
BUNDLETOOL_JAR = os.path.join(TOOLS_DIR, "bundletool-all.jar")

KEYSTORE_PATH = os.path.join(ROOT, "pcdeck_release.keystore")
KEYSTORE_PASS = "pcdeck2026"
KEY_ALIAS = "pcdeckkey"
KEY_PASS = "pcdeck2026"

AAPT2 = r"C:\Android\build-tools\36.0.0\aapt2.exe"
D8 = r"C:\Android\build-tools\36.0.0\d8.bat"
ANDROID_JAR = r"C:\Android\platforms\android-36\android.jar"

OUTPUT_AAB = os.path.join(ROOT, "PCDeck.aab")
WEBSITE_AAB = os.path.join(ROOT, "website", "PCDeck.aab")

def sync_assets():
    print("[+] Syncing static assets into android_app/assets/...")
    src = os.path.join(ROOT, "static")
    dst = os.path.join(ROOT, "android_app", "assets")
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_root = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target_root, exist_ok=True)
        for f in files:
            s_file = os.path.join(root, f)
            d_file = os.path.join(target_root, f)
            shutil.copy2(s_file, d_file)
    print("    OK: Static assets synced.")

def ensure_bundletool():
    if not os.path.exists(BUNDLETOOL_JAR) or os.path.getsize(BUNDLETOOL_JAR) < 10000000:
        print("[+] Downloading Google bundletool...")
        os.makedirs(TOOLS_DIR, exist_ok=True)
        url = "https://github.com/google/bundletool/releases/download/1.17.0/bundletool-all-1.17.0.jar"
        urllib.request.urlretrieve(url, BUNDLETOOL_JAR)
        print("    OK: bundletool downloaded.")

def run_cmd(cmd, check=True):
    print(f"    Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    res = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if res.returncode != 0 and check:
        print(f"[-] ERROR: Command failed with code {res.returncode}")
        print("STDOUT:\n" + res.stdout)
        print("STDERR:\n" + res.stderr)
        sys.exit(1)
    return res

def main():
    print("=" * 60)
    print("      [+] BUILDING SIGNED PLAY STORE APP BUNDLE (.AAB)")
    print("=" * 60)

    sync_assets()
    ensure_bundletool()

    # Clean previous build artifacts
    for d in [OBJ_DIR, GEN_DIR, DEX_DIR, MODULE_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    # 1. Compile Resources with AAPT2
    print("\n[+] 1. Compiling Android Resources...")
    res_zip = os.path.join(BUILD_DIR, "res.zip")
    if os.path.exists(res_zip):
        os.remove(res_zip)
    run_cmd(f'"{AAPT2}" compile --dir android_app/res -o "{res_zip}"')

    # 2. Link in proto format for App Bundle
    print("\n[+] 2. Linking Resources in Proto format (aapt2 --proto-format)...")
    manifest = os.path.join(ROOT, "android_app", "AndroidManifest.xml")
    assets_dir = os.path.join(ROOT, "android_app", "assets")
    proto_apk = os.path.join(BUILD_DIR, "base_proto.apk")
    if os.path.exists(proto_apk):
        os.remove(proto_apk)

    cmd_link = (
        f'"{AAPT2}" link --proto-format -o "{proto_apk}" '
        f'-I "{ANDROID_JAR}" --manifest "{manifest}" '
        f'-A "{assets_dir}" --java "{GEN_DIR}" '
        f'"{res_zip}" --min-sdk-version 21 --target-sdk-version 36 --auto-add-overlay'
    )
    run_cmd(cmd_link)

    # 3. Compile Java sources
    print("\n[+] 3. Compiling Java Source Files...")
    java_files = []
    for r, _, files in os.walk(os.path.join(ROOT, "android_app", "src")):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(r, f))
    for r, _, files in os.walk(GEN_DIR):
        for f in files:
            if f.endswith(".java"):
                java_files.append(os.path.join(r, f))

    cmd_javac = [
        "javac", "-encoding", "UTF-8",
        "-cp", ANDROID_JAR,
        "-d", OBJ_DIR
    ] + java_files
    run_cmd(cmd_javac)

    # 4. Convert .class files to DEX
    print("\n[+] 4. Converting to DEX format (d8)...")
    class_files = []
    for r, _, files in os.walk(OBJ_DIR):
        for f in files:
            if f.endswith(".class"):
                class_files.append(os.path.join(r, f))

    cmd_d8 = [D8, "--output", DEX_DIR] + class_files
    run_cmd(cmd_d8)

    # 5. Extract proto APK and assemble base module structure
    print("\n[+] 5. Assembling App Bundle Base Module Structure...")
    with zipfile.ZipFile(proto_apk, "r") as z:
        z.extractall(MODULE_DIR)

    # In base module, move AndroidManifest.xml into manifest/
    manifest_dst_dir = os.path.join(MODULE_DIR, "manifest")
    os.makedirs(manifest_dst_dir, exist_ok=True)
    shutil.move(os.path.join(MODULE_DIR, "AndroidManifest.xml"), os.path.join(manifest_dst_dir, "AndroidManifest.xml"))

    # Copy DEX files into dex/
    dex_dst_dir = os.path.join(MODULE_DIR, "dex")
    os.makedirs(dex_dst_dir, exist_ok=True)
    for f in os.listdir(DEX_DIR):
        if f.endswith(".dex"):
            shutil.copy2(os.path.join(DEX_DIR, f), os.path.join(dex_dst_dir, f))

    # Zip the base module directory into base.zip
    base_zip = os.path.join(BUILD_DIR, "base.zip")
    if os.path.exists(base_zip):
        os.remove(base_zip)

    with zipfile.ZipFile(base_zip, "w", zipfile.ZIP_DEFLATED) as z_out:
        for r, _, files in os.walk(MODULE_DIR):
            for f in files:
                full_path = os.path.join(r, f)
                rel_path = os.path.relpath(full_path, MODULE_DIR)
                z_out.write(full_path, rel_path)

    print("    OK: base.zip module created.")

    # 6. Build App Bundle using bundletool
    print("\n[+] 6. Building App Bundle with bundletool...")
    unsigned_aab = os.path.join(BUILD_DIR, "unsigned.aab")
    if os.path.exists(unsigned_aab):
        os.remove(unsigned_aab)

    cmd_bundle = [
        "java", "-jar", BUNDLETOOL_JAR,
        "build-bundle",
        f"--modules={base_zip}",
        f"--output={unsigned_aab}"
    ]
    run_cmd(cmd_bundle)

    # 7. Sign AAB with jarsigner
    print("\n[+] 7. Signing App Bundle with Release Keystore (jarsigner)...")
    if os.path.exists(OUTPUT_AAB):
        os.remove(OUTPUT_AAB)
    shutil.copy2(unsigned_aab, OUTPUT_AAB)

    cmd_sign = [
        "jarsigner",
        "-keystore", KEYSTORE_PATH,
        "-storepass", KEYSTORE_PASS,
        "-keypass", KEY_PASS,
        "-sigalg", "SHA256withRSA",
        "-digestalg", "SHA-256",
        OUTPUT_AAB,
        KEY_ALIAS
    ]
    run_cmd(cmd_sign)

    # 8. Validate Bundle
    print("\n[+] 8. Validating Signed App Bundle...")
    cmd_val = [
        "java", "-jar", BUNDLETOOL_JAR,
        "validate",
        f"--bundle={OUTPUT_AAB}"
    ]
    run_cmd(cmd_val)
    print("    OK: App Bundle validated successfully!")

    # Copy to website folder
    os.makedirs(os.path.dirname(WEBSITE_AAB), exist_ok=True)
    shutil.copy2(OUTPUT_AAB, WEBSITE_AAB)

    size_kb = os.path.getsize(OUTPUT_AAB) / 1024
    print("=" * 60)
    print(f"OK: SUCCESS: Signed Play Store Bundle generated at:")
    print(f"    '{OUTPUT_AAB}' ({size_kb:.1f} KB)")
    print("=" * 60)

if __name__ == "__main__":
    main()
