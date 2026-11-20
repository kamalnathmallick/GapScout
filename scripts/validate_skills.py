"""Validator script for Agent Skills frontmatter and markdown structure."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def validate_skills() -> int:
    """Validate all SKILL.md files under skills/ directory."""
    if not SKILLS_DIR.exists():
        print(f"Error: {SKILLS_DIR} not found.")
        return 1

    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_files:
        print("Error: No SKILL.md files found in skills/.")
        return 1

    errors = 0
    print(f"Validating {len(skill_files)} skill definition(s)...")

    for sf in skill_files:
        rel_path = sf.relative_to(REPO_ROOT)
        text = sf.read_text(encoding="utf-8")

        if not text.startswith("---"):
            print(f"[{rel_path}] FAIL: Missing YAML frontmatter start ('---')")
            errors += 1
            continue

        parts = text.split("---", 2)
        if len(parts) < 3:
            print(f"[{rel_path}] FAIL: Malformed YAML frontmatter (missing closing '---')")
            errors += 1
            continue

        frontmatter = parts[1]
        body = parts[2].strip()

        # Parse simple frontmatter keys
        name = None
        desc = None
        for line in frontmatter.strip().splitlines():
            line = line.strip()
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()

        if not name:
            print(f"[{rel_path}] FAIL: Missing 'name' in frontmatter")
            errors += 1
        elif name != sf.parent.name:
            print(
                f"[{rel_path}] FAIL: Skill name '{name}' does not match directory '{sf.parent.name}'"
            )
            errors += 1

        if not desc:
            print(f"[{rel_path}] FAIL: Missing 'description' in frontmatter")
            errors += 1

        if not body:
            print(f"[{rel_path}] FAIL: Empty body in markdown file")
            errors += 1

        if not errors:
            print(f"[{rel_path}] PASS: {name} (valid frontmatter & body)")

    if errors > 0:
        print(f"\nSkills validation failed with {errors} error(s).")
        return 1

    print("\nAll skills passed validation successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(validate_skills())
