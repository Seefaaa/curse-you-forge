"""
Patcher for CurseForge to hide the ad element in the app
"""

import ctypes
from ctypes import wintypes
import fnmatch
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

from asar import AsarArchive # pyright: ignore[reportMissingTypeStubs]

kernel32 = ctypes.windll.kernel32

BeginUpdateResource = kernel32.BeginUpdateResourceW
UpdateResource = kernel32.UpdateResourceW
EndUpdateResource = kernel32.EndUpdateResourceW

BeginUpdateResource.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
BeginUpdateResource.restype = wintypes.HANDLE

UpdateResource.argtypes = [
    wintypes.HANDLE,   # handle
    wintypes.LPCWSTR,  # type
    wintypes.LPCWSTR,  # name
    wintypes.WORD,     # lang
    wintypes.LPVOID,   # data
    wintypes.DWORD     # data size
]
UpdateResource.restype = wintypes.BOOL

EndUpdateResource.argtypes = [wintypes.HANDLE, wintypes.BOOL]
EndUpdateResource.restype = wintypes.BOOL

def patch_resource(exe_path: Path, resource_type: str, resource_name: str, lang_id: int, data: bytes):
    """patch a resource in the executable with the given data"""

    handle = BeginUpdateResource(str(exe_path), False)
    if not handle:
        raise ctypes.WinError()

    if not UpdateResource(
        handle,
        resource_type,
        resource_name,
        lang_id,
        data,
        len(data)
    ):
        raise ctypes.WinError()

    if not EndUpdateResource(handle, False):
        raise ctypes.WinError()

def patch_integrity_resource(exe_path: Path, data: bytes):
    """patch the INTEGRITY resource added by electron with the given data"""
    patch_resource(
        exe_path,
        "INTEGRITY",  # resource type
        "ELECTRONASAR",  # resource name
        0x0409,  # en-US locale
        data
    )

def patch_css(css_path: Path):
    """patch the desktop.css file to hide the ad element"""
    css_content = ".curseforge-ad { display: none !important; }\n"
    with open(css_path, "a", encoding="utf-8") as f:
        f.write(css_content)

class AsarArchiveExt(AsarArchive):
    raw_header: bytes
    def _read_from_asar(self):
        _data_size, header_size, _header_object_size, header_string_size = struct.unpack(
            "<4I", self._asar_io.read(16)
        )
        self.raw_header = self._asar_io.read(header_string_size)
        header = json.loads(self.raw_header.decode("utf-8"))
        self._offset = 8 + header_size
        self._parse_metadata(header, Path(""))
    def _pack(self, path: Path, src: Path, unpack: str):
        unpack_list = unpack.split(",") if unpack else []
        path_in = path.relative_to(src)
        if path.is_symlink():
            node = self._search_node_from_path(path_in)
            node.set_link(path.resolve().relative_to(src))
            if node.link.parts[0] == "..":
                raise ValueError(f'${path_in}: file "{node.link}" links out of the package')
        elif path.is_dir():
            node = self._search_node_from_path(path_in)
            node.set_dir(unpacked=any(fnmatch.fnmatch(path.name, pattern) for pattern in unpack_list) if unpack else False)
            for child in path.iterdir():
                self._pack(child, src, unpack)
        else:
            self.pack_file(path_in, path, should_unpack=any(fnmatch.fnmatch(path.name, pattern) for pattern in unpack_list) if unpack else False)

def main():
    # path to the CurseForge installation directory
    curse_path = Path.home() / "AppData" / "Local" / "Programs" / "CurseForge Windows"
    if not curse_path.exists():
        if len(sys.argv) < 2:
            print("could not find CurseForge installation directory, try giving the path as an argument")
            return
        else:
            curse_path = Path(sys.argv[1])
        if not curse_path.exists():
            print("invalid path provided")
            return

    # path to the executable to patch
    exe_path = curse_path / "CurseForge.exe"
    # path to the asar file to extract and patch
    asar_path = curse_path / "resources" / "app.asar"
    # path to the asar unpacked directory
    asar_unpacked_path = curse_path / "resources" / "app.asar.unpacked"
    # path to extract the asar contents to
    extract_path = curse_path / "resources" / "extracted_app"

    # backup the original executable
    backup_exe_path = Path(f"{exe_path}.bak")
    if not backup_exe_path.exists():
        print("backing up original executable...")
        shutil.copy2(exe_path, backup_exe_path)

    # backup the original asar
    backup_asar_path = Path(f"{asar_path}.bak")
    backup_unpacked_path = Path(f"{backup_asar_path}.unpacked")
    if not backup_asar_path.exists():
        print("backing up original asar...")
        shutil.copy2(asar_path, backup_asar_path)
    if not backup_unpacked_path.exists():
        print("backing up original asar unpacked directory...")
        shutil.copytree(asar_unpacked_path, backup_unpacked_path)

    print("extracting asar...")
    if extract_path.exists():
        shutil.rmtree(extract_path) # ensure the extract path is clean
    with AsarArchiveExt(backup_asar_path, "r") as archive:
        archive.extract(extract_path)

    print("patching css...")
    patch_css(extract_path / "dist" / "desktop" / "desktop.css")

    print("creating patched asar...")
    if asar_path.exists():
        asar_path.unlink()
    if asar_unpacked_path.exists():
        shutil.rmtree(asar_unpacked_path)
    with AsarArchiveExt(asar_path, "w") as archive:
        archive.pack(extract_path, "*.exe,*.dll,minecraft-custom-profile.webp,vanilla-modpack.webp")

    # cleanup extracted files
    shutil.rmtree(extract_path)

    with AsarArchiveExt(asar_path, "r") as archive:
        hash = hashlib.sha256(archive.raw_header).hexdigest()

    print(f"calculated hash: {hash}")

    # resource data
    data = f'[{{"file":"resources\\\\app.asar","alg":"SHA256","value":"{hash}"}}]'

    print("patching executable...")
    patch_integrity_resource(exe_path, data.encode("utf-8"))

    print("done!")

if __name__ == "__main__":
    main()
