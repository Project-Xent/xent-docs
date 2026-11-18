import os
import shutil

_here = os.path.dirname(__file__)
_workspace = os.path.abspath(os.path.join(_here, "..", ".."))


def _compiler():
    """Prefer a Clang whose default target is the Windows SDK.

    ``clang`` on PATH may be a MinGW build. Its headers do not parse
    ``<windows.h>``, which the Fluxent reference includes.
    """
    if os.name == "nt":
        preferred = os.path.join(
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            "LLVM",
            "bin",
            "clang.exe",
        )
        if os.path.isfile(preferred):
            return preferred
    return shutil.which("clang")

project = "Xent"
author = "Project Xent"
copyright = "2026, Project Xent"
release = "0.3.3"
version = "0.3.3"

extensions = ["hawkmoth"]
primary_domain = "c"
templates_path = ["_templates"]
exclude_patterns = []
locale_dirs = ["locale/"]
gettext_compact = False
html_theme = "library"
html_theme_options = {
    "description": "Native cross-platform UI in C23.",
    "show_version": True,
}
html_sidebars = {
    "**": [
        "about.html",
        "searchbox.html",
        "globaltoc.html",
        "localtoc.html",
        "readingmodes.html",
    ]
}
html_static_path = ["_static"]

hawkmoth_root = _workspace
hawkmoth_compiler = _compiler()
hawkmoth_clang = [
    "-std=c23",
    "-I" + os.path.join(_workspace, "xent-core", "include"),
    "-I" + os.path.join(_workspace, "xent-kit", "include"),
    "-I" + os.path.join(_workspace, "fluxent", "include"),
    "-I" + os.path.join(_workspace, "cwinrt", "include"),
]
if os.name == "nt":
    hawkmoth_clang.insert(0, "--target=x86_64-pc-windows-msvc")
