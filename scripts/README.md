# Utility Scripts

This directory contains utility scripts for the StoryProof project.

## Scripts

### `merge_novels.py`
Merges multiple text files (e.g., novel chapters) into a single file with separators.

**Usage:**
```bash
python scripts/merge_novels.py [options]
```

**Options:**
- `--input_dir`, `-i`: Directory containing text files (default: `.`)
- `--output`, `-o`: Output filename (default: `merged_novel.txt`)
- `--pattern`, `-p`: File pattern to match (default: `*.txt`)

**Example:**
```bash
python scripts/merge_novels.py --input_dir "path/to/chapters" --output "full_novel.txt"
```
