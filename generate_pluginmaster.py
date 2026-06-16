"""
Dalamud 插件仓库清单生成脚本

自动扫描 plugins/ 目录下的插件，生成 pluginmaster.json
"""
import json
import os
from os.path import getmtime
from zipfile import ZipFile

# 修改为你的仓库信息
GITHUB_REPO = "Kirei1i/Plugins"
BRANCH = os.environ.get("GITHUB_REF", "refs/heads/main").split("refs/heads/")[-1]

DOWNLOAD_URL = f"https://github.com/{GITHUB_REPO}/raw/{{branch}}/plugins/{{plugin_name}}/latest.zip"
TESTING_DOWNLOAD_URL = f"https://github.com/{GITHUB_REPO}/raw/{{branch}}/plugins/{{plugin_name}}/testing/latest.zip"
SUB_DOWNLOAD_URL = f"https://github.com/{GITHUB_REPO}/raw/{{branch}}/plugins/{{plugin_name}}/{{subfolder}}/latest.zip"

# pluginmaster.json 中保留的字段
TRIMMED_KEYS = [
    "Author",
    "Name",
    "Punchline",
    "Description",
    "Tags",
    "InternalName",
    "RepoUrl",
    "Changelog",
    "AssemblyVersion",
    "ApplicableVersion",
    "DalamudApiLevel",
    "TestingAssemblyVersion",
    "TestingDalamudApiLevel",
    "IconUrl",
    "ImageUrls",
    "Subfolder",
]

# DownloadLinkUpdate 默认等于 DownloadLinkInstall
DUPLICATES = {
    "DownloadLinkInstall": ["DownloadLinkUpdate"],
}


def main():
    master = extract_manifests()
    master = [trim_manifest(m) for m in master]
    add_extra_fields(master)
    write_master(master)
    update_last_update()
    print(f"Generated pluginmaster.json with {len(master)} plugin(s)")


def extract_manifests():
    """从 plugins/ 目录提取所有插件清单"""
    manifests = []
    plugins_root = os.path.join(".", "plugins")

    if not os.path.isdir(plugins_root):
        return manifests

    for plugin_folder in sorted(os.listdir(plugins_root)):
        plugin_dir = os.path.join(plugins_root, plugin_folder)
        if not os.path.isdir(plugin_dir):
            continue

        plugin_name = plugin_folder
        base_zip = os.path.join(plugin_dir, "latest.zip")

        if not os.path.exists(base_zip):
            print(f"Skipping {plugin_name}: no latest.zip found")
            continue

        # 读取主清单
        with ZipFile(base_zip) as z:
            # 清单文件名通常是 <InternalName>.json
            manifest_file = None
            for name in z.namelist():
                if name.endswith(".json") and "/" not in name:
                    manifest_file = name
                    break

            if manifest_file is None:
                print(f"Skipping {plugin_name}: no manifest found in zip")
                continue

            base_manifest = json.loads(z.read(manifest_file).decode("utf-8"))
            base_manifest["Subfolder"] = None

            # 检查是否有测试版本
            testing_zip = os.path.join(plugin_dir, "testing", "latest.zip")
            if os.path.exists(testing_zip):
                with ZipFile(testing_zip) as tz:
                    testing_manifest = json.loads(
                        tz.read(manifest_file).decode("utf-8")
                    )
                    base_manifest["TestingAssemblyVersion"] = testing_manifest.get(
                        "AssemblyVersion"
                    )
                    base_manifest["TestingDalamudApiLevel"] = testing_manifest.get(
                        "DalamudApiLevel"
                    )

            manifests.append(base_manifest)

        # 扫描子目录（如 API13、API14 等旧版本）
        for sub in sorted(os.listdir(plugin_dir)):
            sub_path = os.path.join(plugin_dir, sub)
            if not os.path.isdir(sub_path) or sub == "testing":
                continue

            sub_zip = os.path.join(sub_path, "latest.zip")
            if os.path.exists(sub_zip):
                with ZipFile(sub_zip) as sz:
                    sub_manifest = json.loads(
                        sz.read(manifest_file).decode("utf-8")
                    )
                    sub_manifest["Subfolder"] = sub
                    sub_manifest["Name"] = f"{sub_manifest['Name']} ({sub})"
                    manifests.append(sub_manifest)

    return manifests


def trim_manifest(manifest):
    """只保留必要字段"""
    return {k: manifest[k] for k in TRIMMED_KEYS if k in manifest}


def add_extra_fields(manifests):
    """添加下载链接等额外字段"""
    for manifest in manifests:
        sub = manifest.get("Subfolder")
        if sub:
            manifest["DownloadLinkInstall"] = SUB_DOWNLOAD_URL.format(
                branch=BRANCH,
                plugin_name=manifest["InternalName"],
                subfolder=sub,
            )
        else:
            manifest["DownloadLinkInstall"] = DOWNLOAD_URL.format(
                branch=BRANCH,
                plugin_name=manifest["InternalName"],
            )

        # 复制字段
        for src, targets in DUPLICATES.items():
            for target in targets:
                if target not in manifest:
                    manifest[target] = manifest[src]

        # 测试版本下载链接
        if "TestingAssemblyVersion" in manifest and not sub:
            manifest["DownloadLinkTesting"] = TESTING_DOWNLOAD_URL.format(
                branch=BRANCH,
                plugin_name=manifest["InternalName"],
            )

        manifest["DownloadCount"] = 0


def write_master(master):
    """写入 pluginmaster.json"""
    for plugin in master:
        plugin.pop("Subfolder", None)

    with open("pluginmaster.json", "w", encoding="utf-8") as f:
        json.dump(master, f, indent=4, ensure_ascii=False)


def update_last_update():
    """更新 LastUpdate 时间戳"""
    with open("pluginmaster.json", encoding="utf-8") as f:
        master = json.load(f)

    for plugin in master:
        sub = plugin.get("Subfolder")
        if sub:
            file_path = os.path.join(
                "plugins", plugin["InternalName"], sub, "latest.zip"
            )
        else:
            file_path = os.path.join(
                "plugins", plugin["InternalName"], "latest.zip"
            )

        if os.path.exists(file_path):
            modified = int(getmtime(file_path))
            if "LastUpdate" not in plugin or modified != int(
                plugin.get("LastUpdate", 0)
            ):
                plugin["LastUpdate"] = str(modified)

    with open("pluginmaster.json", "w", encoding="utf-8") as f:
        json.dump(master, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
