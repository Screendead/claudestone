"""Build the redstone-satellite image on the desktop's Docker:

    python -m scripts.satellite_image [--no-cache]

The context is streamed as a tar (the laptop has no buildx, and the desktop's legacy
builder takes a context on stdin): docker/satellite/ plus server/server.jar. macOS
extended attributes and AppleDouble files are left out, or they land in the image.
"""

import os
import subprocess
import sys
from pathlib import Path

from redstone.docker_sats import CONTEXT, IMAGE

REPO = Path(__file__).resolve().parent.parent
FILES = ("Dockerfile", "server.properties", "pregen.sh", "start.sh")


def commands(no_cache: bool = False) -> tuple[list[str], list[str]]:
    tar = ["tar", "--no-xattrs", "--no-mac-metadata", "-cf", "-", "-C", str(REPO / "docker" / "satellite"),
           *FILES, "-C", str(REPO / "server"), "server.jar"]
    build = ["docker", "--context", CONTEXT, "build", *(["--no-cache"] if no_cache else []), "-t", IMAGE, "-"]
    return tar, build


def main(argv: list[str]) -> int:
    tar_cmd, build_cmd = commands("--no-cache" in argv)
    tar = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, env={**os.environ, "COPYFILE_DISABLE": "1"})
    built = subprocess.run(build_cmd, stdin=tar.stdout)
    tar.stdout.close()
    if tar.wait() != 0:
        print("tar failed", file=sys.stderr)
        return 1
    return built.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
