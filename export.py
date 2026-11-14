import os
from pathlib import Path

# Folder to scan
SOURCE_FOLDER = r"C:\Users\udhay\Downloads\bharathi_oil_mill\bharathi_oil_mill"

# Output file
OUTPUT_FILE = "project_code_dump.txt"

# Code file extensions
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".cs", ".cpp", ".c", ".h",
    ".php", ".go", ".rs", ".swift",
    ".html", ".css", ".scss",
    ".sql", ".json", ".yaml", ".yml",
    ".xml", ".sh", ".bat", ".ps1",
    ".dart", ".kt", ".vue"
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

    outfile.write("=" * 120 + "\n")
    outfile.write("PROJECT CODE EXPORT\n")
    outfile.write("=" * 120 + "\n\n")

    for root, dirs, files in os.walk(SOURCE_FOLDER):

        # Ignore common folders
        dirs[:] = [
            d for d in dirs
            if d not in {
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                "node_modules",
                ".next",
                "dist",
                "build"
            }
        ]

        for file in files:

            filepath = os.path.join(root, file)
            ext = Path(file).suffix.lower()

            if ext not in CODE_EXTENSIONS:
                continue

            try:
                relative_path = os.path.relpath(
                    filepath,
                    SOURCE_FOLDER
                )

                with open(
                    filepath,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:
                    content = f.read()

                outfile.write("\n")
                outfile.write("=" * 120 + "\n")
                outfile.write(f"FILE: {file}\n")
                outfile.write(f"PATH: {filepath}\n")
                outfile.write(f"RELATIVE_PATH: {relative_path}\n")
                outfile.write(f"EXTENSION: {ext}\n")
                outfile.write("=" * 120 + "\n\n")

                outfile.write(content)
                outfile.write("\n\n")

            except Exception as e:
                outfile.write(
                    f"\nERROR READING {filepath}: {str(e)}\n"
                )

print(f"Export completed: {OUTPUT_FILE}")
