import os
import glob
import argparse
import re

def sort_key(filename):
    """
    Sort files numerically if possible (e.g., '1.txt', '10.txt'), 
    otherwise alphabetically.
    Returns a tuple to ensure consistent types for comparison.
    """
    basename = os.path.basename(filename)
    # Extract number from filename if it starts with a number
    match = re.match(r'(\d+)', basename)
    if match:
        # (priority, number) - numbers come first
        return (0, int(match.group(1)))
    # (priority, string) - non-numbers come after
    return (1, basename)

def merge_files(input_dir, output_file, pattern="*.txt"):
    """
    Merges text files in the input directory into a single output file.
    
    Args:
        input_dir (str): Directory containing text files to merge.
        output_file (str): Path to the output file.
        pattern (str): Glob pattern for filtering files (default: "*.txt").
    """
    
    # 1. Find all files
    search_path = os.path.join(input_dir, pattern)
    files = glob.glob(search_path)
    
    # Exclude output file if it exists in the list to prevent self-inclusion
    abs_output = os.path.abspath(output_file)
    files = [f for f in files if os.path.abspath(f) != abs_output]
    
    if not files:
        print(f"No files found in {input_dir} matching {pattern}")
        return

    # 2. Sort files naturally
    files.sort(key=sort_key)
    print(f"Found {len(files)} files to merge.")

    merged_content = []

    # 3. Read and merge
    for file_path in files:
        filename = os.path.basename(file_path)
        # Remove extension for title
        title = os.path.splitext(filename)[0]
        
        try:
            # Read as binary to detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # Detect encoding
            import chardet
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            
            content = None
            if encoding and result['confidence'] > 0.7:
                try:
                    content = raw_data.decode(encoding).strip()
                except:
                    pass
            
            # Fallback if detection failed or decoding failed
            if content is None:
                encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-16', 'latin-1']
                for enc in encodings:
                    try:
                        content = raw_data.decode(enc).strip()
                        break
                    except:
                        continue
            
            if content is None:
                print(f"Error reading {filename}: Cannot detect encoding")
                continue
                
            # Header format from backend logic
            header = f"\n\n--- {title} 시작 ---\n"
            merged_content.append(header + content)
            print(f"Processed: {filename}")
            
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    # 4. Write output
    final_content = "".join(merged_content).strip()
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"\nSuccessfully merged {len(files)} files into {output_file}")
        
    except Exception as e:
        print(f"Error writing to output file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge text files/chapters into a single novel file.")
    parser.add_argument("--input_dir", "-i", default=".", help="Directory containing text files (default: current directory)")
    parser.add_argument("--output", "-o", default="merged_novel.txt", help="Output filename (default: merged_novel.txt)")
    parser.add_argument("--pattern", "-p", default="*.txt", help="File pattern to match (default: *.txt)")
    
    args = parser.parse_args()
    
    # Ensure input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
    else:
        merge_files(args.input_dir, args.output, args.pattern)
