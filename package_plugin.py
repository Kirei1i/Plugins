"""
插件打包脚本

用法: python package_plugin.py <插件目录> <编译输出目录>

示例: python package_plugin.py plugins/PartyIcons ../xivPartyIcons/PartyIcons/bin/Release/net8.0-windows
"""
import json
import sys
import os
from zipfile import ZipFile, ZIP_DEFLATED


def package_plugin(plugin_dir: str, build_dir: str):
    """
    将编译好的插件打包成 latest.zip

    Args:
        plugin_dir: 插件目录路径 (如 plugins/PartyIcons)
        build_dir: 编译输出目录 (含 PartyIcons.dll 和 PartyIcons.json)
    """
    # 查找清单文件
    manifest_file = None
    for f in os.listdir(build_dir):
        if f.endswith(".json"):
            manifest_file = f
            break

    if manifest_file is None:
        print("错误: 在编译输出目录中找不到清单文件 (.json)")
        return False

    # 读取清单获取内部名称
    with open(os.path.join(build_dir, manifest_file), "r", encoding="utf-8") as f:
        manifest = json.load(f)

    internal_name = manifest.get("InternalName")
    if not internal_name:
        print("错误: 清单文件中缺少 InternalName 字段")
        return False

    # 同时更新插件目录中的清单文件
    plugin_manifest = os.path.join(plugin_dir, f"{internal_name}.json")
    with open(plugin_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"已更新清单: {plugin_manifest}")

    # 创建 zip 文件
    zip_path = os.path.join(plugin_dir, "latest.zip")
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        # 添加清单文件
        zf.write(
            os.path.join(build_dir, manifest_file),
            manifest_file,
        )

        # 添加 DLL 文件
        dll_file = f"{internal_name}.dll"
        dll_path = os.path.join(build_dir, dll_file)
        if os.path.exists(dll_path):
            zf.write(dll_path, dll_file)
            print(f"已添加: {dll_file}")
        else:
            print(f"警告: 找不到 {dll_file}")

        # 添加其他资源文件 (可选)
        for ext in [".png", ".jpg", ".txt"]:
            for f in os.listdir(build_dir):
                if f.endswith(ext):
                    zf.write(os.path.join(build_dir, f), f)
                    print(f"已添加: {f}")

    print(f"\n打包完成: {zip_path}")

    # 显示版本信息
    version = manifest.get("AssemblyVersion", "未知")
    api_level = manifest.get("DalamudApiLevel", "未知")
    print(f"  插件名称: {manifest.get('Name', '未知')}")
    print(f"  版本: {version}")
    print(f"  API级别: {api_level}")

    return True


def main():
    if len(sys.argv) < 3:
        print("用法: python package_plugin.py <插件目录> <编译输出目录>")
        print("示例: python package_plugin.py plugins/PartyIcons ../xivPartyIcons/bin/Release/net8.0-windows")
        sys.exit(1)

    plugin_dir = sys.argv[1]
    build_dir = sys.argv[2]

    if not os.path.isdir(plugin_dir):
        print(f"错误: 插件目录不存在: {plugin_dir}")
        sys.exit(1)

    if not os.path.isdir(build_dir):
        print(f"错误: 编译输出目录不存在: {build_dir}")
        sys.exit(1)

    success = package_plugin(plugin_dir, build_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
