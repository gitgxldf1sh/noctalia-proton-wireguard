#!/usr/bin/env python3
"""Static checks for the plugin: manifest, translations and the keys the code uses."""
import glob
import json
import re
import sys
import tomllib

errors = []


def flat(node, prefix=""):
    out = {}
    for key, value in node.items():
        if isinstance(value, dict):
            out.update(flat(value, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = value
    return out


with open("plugin.toml", "rb") as fh:
    manifest = tomllib.load(fh)
if not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
    errors.append("plugin.toml: version must look like 1.2.3")
for kind in ("service", "widget", "panel", "shortcut"):
    for entry in manifest.get(kind, []):
        try:
            open(entry["entry"]).close()
        except OSError:
            errors.append(f"plugin.toml: missing entry file {entry['entry']}")

langs = {}
for path in sorted(glob.glob("translations/*.json")):
    with open(path, encoding="utf-8") as fh:
        langs[path] = flat(json.load(fh))
base = langs["translations/en.json"]
for path, keys in langs.items():
    for key in sorted(set(base) - set(keys)):
        errors.append(f"{path}: missing key {key}")
    for key in sorted(set(keys) - set(base)):
        errors.append(f"{path}: key {key} is not in en.json")
    for key in sorted(set(base) & set(keys)):
        if set(re.findall(r"\{(\w+)\}", base[key])) != set(re.findall(r"\{(\w+)\}", keys[key])):
            errors.append(f"{path}: placeholders of {key} differ from en.json")

used = set()
for setting in manifest.get("setting", []):
    used.update(v for k, v in setting.items() if k.endswith("_key"))
    used.update(o["label_key"] for o in setting.get("options", []) if "label_key" in o)
sections = "|".join(sorted({k.split(".")[0] for k in base if "." in k}))
for path in glob.glob("*.luau"):
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    used.update(re.findall(rf'"((?:{sections})\.[a-z0-9_.]+)"', source))
    used.update(re.findall(r'\btr\("([a-z0-9_.]+)"', source))
for key in sorted(used - set(base)):
    errors.append(f"translation key {key} is used but not defined")

for line in errors:
    print(line)
print(f"{len(errors)} problem(s)")
sys.exit(1 if errors else 0)
