# Curse-You-Forge

Hides ad elements in the CurseForge desktop app by simply patching its CSS code.

## Running the Script

You have two options:

- Get the script [here](https://github.com/Seefaaa/curse-you-forge/blob/master/main.py) and run it with Python 3.14 or higher.
- Download the executeable from [here](https://github.com/Seefaaa/curse-you-forge/releases/tag/latest) and simply run it.

*The executeable is just a Python binary with this script embeded.*

> [!NOTE]  
> Needs to be done after every CurseForge update.

> [!CAUTION]
> Works on Windows only!

## How?

Since the app is built with Electron, it's simple to unpack, modify and repack the app's code.

Therefore, what this script does is simple:

- Locate CurseForge installation (script only looks for the default installation path or you need to provide it manually).
- Extract its `asar` (the thing Electron bundles the app code into) archive.
- Inject `.curseforge-ad { display: none !important; }` into `desktop.css`.
- Archive back.
- Modify CurseForge executeable's resource and replace old archive's engraved hash with this new one's.

### Resource

In brief, Electron does intregrity checks by checking the [executeable's resource](https://en.wikipedia.org/wiki/Resource_%28Windows%29) to determine whether the `asar` archive is modified or not before the app runs.
If it's modified and the embeded hash in the resource does not match the archive's, it simply refuses to run.

Modifying an executeable's resource is pretty simple in Windows, can be done by just using [Win32](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-updateresourcea).

And this is the part that makes this script Windows only.

If you are a Loonix user reading this, I would be glad if you work out Loonix equivelent of this step and create a Pull Request.

# Citations

See [this blog post](https://noh.am/en/posts/unpacking-and-repacking-electron-apps/), which showed me how simple unpacking and repacking an electron app is.
