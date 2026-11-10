import os
import re
import xml.etree.ElementTree as ET

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')

def patch_manifest(work_dir):
    manifest_path = os.path.join(work_dir, "AndroidManifest.xml")
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    # 1. Add touchscreen & leanback requirements set to false
    features = [
        ("android.hardware.touchscreen", "false"),
        ("android.software.leanback", "false")
    ]
    for feat_name, req in features:
        existing = any(f.get(f"{ANDROID_NS}name") == feat_name for f in root.findall("uses-feature"))
        if not existing:
            elem = ET.Element("uses-feature", {
                f"{ANDROID_NS}name": feat_name,
                f"{ANDROID_NS}required": req
            })
            root.insert(0, elem)

    # 2. Modify activities: force landscape and add LEANBACK_LAUNCHER
    application = root.find("application")
    if application is not None:
        for activity in application.findall("activity"):
            # Set to landscape
            activity.set(f"{ANDROID_NS}screenOrientation", "landscape")

            # Check if this activity is the launcher
            for intent_filter in activity.findall("intent-filter"):
                is_main = any(a.get(f"{ANDROID_NS}name") == "android.intent.action.MAIN" for a in intent_filter.findall("action"))
                if is_main:
                    has_leanback = any(c.get(f"{ANDROID_NS}name") == "android.intent.category.LEANBACK_LAUNCHER" for c in intent_filter.findall("category"))
                    if not has_leanback:
                        intent_filter.append(ET.Element("category", {
                            f"{ANDROID_NS}name": "android.intent.category.LEANBACK_LAUNCHER"
                        }))

    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)
    print("[✓] AndroidManifest.xml successfully patched.")

def patch_smali(work_dir):
    # Scan smali folders to force landscape in hardcoded code (0x1 -> 0x0)
    for root_dir, _, files in os.walk(work_dir):
        for file in files:
            if file.endswith(".smali"):
                file_path = os.path.join(root_dir, file)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # If the file calls setRequestedOrientation, replace portrait flag (0x1) with landscape (0x0)
                if "setRequestedOrientation" in content:
                    patched = re.sub(r'const/4\s+(v\d+),\s+0x1(?=\s+invoke-virtual\s+\{[^}]+\},\s+Landroid/app/Activity;->setRequestedOrientation)',
                                     r'const/4 \1, 0x0', content)
                    if patched != content:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(patched)
                        print(f"[✓] Patched hardcoded orientation in: {file}")

if __name__ == "__main__":
    work_directory = "decompiled"
    patch_manifest(work_directory)
    patch_smali(work_directory)
