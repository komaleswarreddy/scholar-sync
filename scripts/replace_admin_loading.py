import re
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "apps" / "web" / "src" / "app" / "admin"
pattern = re.compile(
    r"  if \(loading\) \{\s*return \(\s*"
    r"<div className=\"h-full flex items-center justify-center\">.*?"
    r"</div>\s*\);\s*\}",
    re.DOTALL,
)

for path in root.rglob("page.tsx"):
    text = path.read_text(encoding="utf-8")
    if "h-full flex items-center justify-center" not in text:
        continue
    new_text, n = pattern.subn("  if (loading) return <AdminTableSkeleton />;", text)
    if not n:
        continue
    if "AdminTableSkeleton" not in new_text.split("export default")[0]:
        lines = new_text.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, "import { AdminTableSkeleton } from '@/components/skeleton';")
        new_text = "\n".join(lines)
    path.write_text(new_text, encoding="utf-8")
    print(f"updated {path} ({n})")
