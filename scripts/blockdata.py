"""Write redstone/blocks.json, the block states and entity types of the server's version,
from the vanilla data generator's reports, for offline checks by scripts.lint.

    python -m scripts.blockdata
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from redstone.harness import SERVER_DIR

OUT = Path(__file__).resolve().parent.parent / "redstone" / "blocks.json"


def generate(jar: Path = SERVER_DIR / "server.jar") -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["java", "-DbundlerMainClass=net.minecraft.data.Main", "-jar", str(jar.resolve()),
                        "--reports", "--output", tmp], cwd=tmp, check=True, capture_output=True)
        reports = Path(tmp) / "reports"
        blocks = json.loads((reports / "blocks.json").read_text())
        registries = json.loads((reports / "registries.json").read_text())
    return {"blocks": {b.removeprefix("minecraft:"): v.get("properties", {}) for b, v in sorted(blocks.items())},
            "entities": sorted(e.removeprefix("minecraft:")
                               for e in registries["minecraft:entity_type"]["entries"])}


def main() -> int:
    data = generate()
    OUT.write_text(json.dumps(data, separators=(",", ":"), sort_keys=True) + "\n")
    print(f"{OUT}: {len(data['blocks'])} blocks, {len(data['entities'])} entity types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
