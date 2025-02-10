#!/usr/bin/env python3
"""
duplicate_processor.py

A script to process a directory (recursively) for duplicate files or folders.
It supports the following commands and options:

Commands:
  --report          : Generate a report of duplicate files or folders.
                      (Defaults to searching for folders if --type is not specified.)
  --move            : Moves duplicate files or folders to a directory.
  --move-out        : Moves files from nested directories to the current directory.
                      If used with --type folder, moves the deepest (last) folder that contains files.
  --delete          : Deletes duplicate files or folders in nested directories while keeping one unique copy.
  --consolidate     : Consolidates all .txt files into one file with unique data.
                      This command only works with --type .txt.
  --help            : Displays this help menu.

Options:
  --type            : Specifies the type of item to process (e.g., file, folder, .txt, .jpg, .zip).
                      Defaults to 'folder' for --report and 'file' for other commands.
  --location        : Specifies a custom path for report, move, or consolidate (e.g., path=c:/app/xxx).
  --name            : Specifies a specific file or folder name to filter operations.
  --cleanup         : When used with --report, generates an empty directories report only;
                      when used with --delete, recursively deletes empty directories from the base directory.
  --search-location : Specifies the base directory for all operations (e.g., path=c:/app/abc or path=/opt/var/data).
                      If not provided, the current working directory is used.
  --all             : When used with --delete, deletes ALL files/folders of the specified type from the base and nested directories.
                      When used with --move, moves ALL files/folders of the specified type from the base and nested directories.
                  
IMPORTANT:
• This script uses simple duplicate detection based on names.
• Always test on noncritical data before using any file‐modifying operation.
"""

import os
import sys
import argparse
import shutil
import json
from datetime import datetime

def print_help():
    help_text = """
Usage: python duplicate_processor.py [command] [options]

Commands:
  --report           Generates a report of duplicate files or folders.
                     Defaults to searching for folders if --type is not specified.
  --move             Moves duplicate files or folders to a directory.
  --move-out         Moves files (or the deepest folder) from nested directories to the current directory.
  --delete           Deletes duplicate files or folders in nested directories while keeping one unique copy.
  --consolidate      Consolidates all .txt files into one file with unique data.
                     This command only works with --type .txt.
  --help             Displays this help menu.

Options:
  --type             Specifies the type of item to process (e.g., file, folder, .txt, .jpg, .zip).
                     Defaults to 'folder' for --report and 'file' for other commands.
  --location         Specifies a custom path for report, move, or consolidate (e.g., path=c:/app/xxx).
  --name             Specifies a specific file or folder name to filter operations.
  --cleanup          When used with --report, generates an empty directories report only;
                     when used with --delete, recursively deletes empty directories from the base directory.
  --search-location  Specifies the base directory for all operations (e.g., path=c:/app/abc or path=/opt/var/data).
                     If not provided, the current working directory is used.
  --all              When used with --delete, deletes ALL files/folders of the specified type;
                     when used with --move, moves ALL files/folders of the specified type.
                     
Examples:
  python duplicate_processor.py --report --type file --location path=c:/app/reports
  python duplicate_processor.py --report
  python duplicate_processor.py --move --type .txt --location path=c:/app/xxx
  python duplicate_processor.py --move-out --type folder
  python duplicate_processor.py --delete --type .jpg
  python duplicate_processor.py --delete --all --type .txt
  python duplicate_processor.py --move --all --type .txt --location path=c:/app/xxx
  python duplicate_processor.py --name myfile.txt --report
  python duplicate_processor.py --report --cleanup
  python duplicate_processor.py --delete --cleanup
  python duplicate_processor.py --consolidate --type .txt --location path=c:/app/consolidated
  python duplicate_processor.py --consolidate --type .txt --search-location path=/opt/var/data
    """
    print(help_text)

def parse_location(location_arg):
    """Extract the path if the argument is provided in the form 'path=...'."""
    if location_arg.startswith("path="):
        return location_arg.split("=", 1)[1]
    return location_arg

def scan_files(base_dir, name_filter=None, ext_filter=None):
    """
    Recursively scan for files in base_dir.
    Returns a dictionary mapping filename to a list of full paths.
    """
    results = {}
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if name_filter and file != name_filter:
                continue
            if ext_filter and os.path.splitext(file)[1].lower() != ext_filter.lower():
                continue
            full_path = os.path.join(root, file)
            results.setdefault(file, []).append(full_path)
    return results

def scan_folders(base_dir, name_filter=None):
    """
    Recursively scan for folders in base_dir.
    Returns a dictionary mapping folder name to a list of full paths.
    """
    results = {}
    for root, dirs, files in os.walk(base_dir):
        for folder in dirs:
            if name_filter and folder != name_filter:
                continue
            full_path = os.path.join(root, folder)
            results.setdefault(folder, []).append(full_path)
    return results

def generate_report(duplicates, report_location):
    """
    Saves the duplicate dictionary as a JSON file to the report_location directory.
    The default directory for reports is now 'reports'.
    If the report file exists, a new file is created with a timestamp appended.
    Also, a total count is added to the report.
    """
    os.makedirs(report_location, exist_ok=True)
    base_filename = "duplicate_report.json"
    report_path = os.path.join(report_location, base_filename)
    
    if os.path.exists(report_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_filename = f"duplicate_report_{timestamp}.json"
        report_path = os.path.join(report_location, base_filename)
    
    total_count = len(duplicates)
    report_data = {
        "total_duplicates": total_count,
        "duplicates": duplicates
    }
    try:
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=4)
        print(f"Duplicate report generated at: {report_path}")
    except Exception as e:
        print(f"Error generating duplicate report: {e}")

def move_duplicates(duplicates, destination, item_type):
    """
    Moves duplicate items (all but the first occurrence in each group) to the destination folder.
    Checks that the source exists before moving.
    """
    os.makedirs(destination, exist_ok=True)
    for name, paths in duplicates.items():
        for path in paths[1:]:
            if not os.path.exists(path):
                print(f"Source not found (already moved or deleted): {path}")
                continue
            try:
                dest_path = os.path.join(destination, os.path.basename(path))
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(os.path.basename(path))
                    counter = 1
                    while os.path.exists(os.path.join(destination, f"{base}_{counter}{ext}")):
                        counter += 1
                    dest_path = os.path.join(destination, f"{base}_{counter}{ext}")
                shutil.move(path, dest_path)
                print(f"Moved: {path} -> {dest_path}")
            except Exception as e:
                print(f"Error moving {path}: {e}")

def move_all_items(results, destination):
    """
    Moves all items found in the provided results dictionary to the destination.
    This is used when --all is provided.
    """
    os.makedirs(destination, exist_ok=True)
    for name, paths in results.items():
        for path in paths:
            if not os.path.exists(path):
                print(f"Source not found (already moved or deleted): {path}")
                continue
            try:
                dest_path = os.path.join(destination, os.path.basename(path))
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(os.path.basename(path))
                    counter = 1
                    while os.path.exists(os.path.join(destination, f"{base}_{counter}{ext}")):
                        counter += 1
                    dest_path = os.path.join(destination, f"{base}_{counter}{ext}")
                shutil.move(path, dest_path)
                print(f"Moved: {path} -> {dest_path}")
            except Exception as e:
                print(f"Error moving {path}: {e}")

def delete_all_items(results, item_type):
    """
    Deletes all items found in the provided results dictionary.
    This is used when --all is provided with --delete.
    """
    for name, paths in results.items():
        for path in paths:
            if not os.path.exists(path):
                print(f"Source not found (already moved or deleted): {path}")
                continue
            try:
                if item_type == "folder":
                    shutil.rmtree(path)
                    print(f"Deleted folder: {path}")
                else:
                    os.remove(path)
                    print(f"Deleted file: {path}")
            except Exception as e:
                print(f"Error deleting {path}: {e}")

def move_out_files(base_dir):
    """
    Moves all files from nested directories (i.e., not in the current directory) into the current directory.
    Checks that the file exists before moving.
    """
    current_dir = os.getcwd()
    files_to_move = []
    for root, dirs, files in os.walk(base_dir):
        if os.path.abspath(root) == os.path.abspath(current_dir):
            continue
        for file in files:
            full_path = os.path.join(root, file)
            if os.path.exists(full_path):
                files_to_move.append(full_path)
    for file_path in files_to_move:
        try:
            dest_path = os.path.join(current_dir, os.path.basename(file_path))
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(os.path.basename(file_path))
                counter = 1
                while os.path.exists(os.path.join(current_dir, f"{base}_{counter}{ext}")):
                    counter += 1
                dest_path = os.path.join(current_dir, f"{base}_{counter}{ext}")
            shutil.move(file_path, dest_path)
            print(f"Moved: {file_path} -> {dest_path}")
        except Exception as e:
            print(f"Error moving {file_path}: {e}")

def move_out_last_folder(base_dir):
    """
    Finds the deepest folder (relative to the current directory) that contains files
    and moves it into the current directory.
    Checks that the source exists before moving.
    """
    current_dir = os.getcwd()
    deepest_folder = None
    max_depth = -1
    for root, dirs, files in os.walk(base_dir):
        if os.path.abspath(root) == os.path.abspath(current_dir):
            continue
        if files:
            rel_path = os.path.relpath(root, current_dir)
            depth = rel_path.count(os.sep)
            if depth > max_depth:
                max_depth = depth
                deepest_folder = root
    if deepest_folder:
        if not os.path.exists(deepest_folder):
            print(f"Deepest folder not found (already moved or deleted): {deepest_folder}")
            return
        try:
            dest_path = os.path.join(current_dir, os.path.basename(deepest_folder))
            if os.path.exists(dest_path):
                counter = 1
                while os.path.exists(os.path.join(current_dir, f"{os.path.basename(deepest_folder)}_{counter}")):
                    counter += 1
                dest_path = os.path.join(current_dir, f"{os.path.basename(deepest_folder)}_{counter}")
            shutil.move(deepest_folder, dest_path)
            print(f"Moved folder: {deepest_folder} -> {dest_path}")
        except Exception as e:
            print(f"Error moving folder {deepest_folder}: {e}")
    else:
        print("No nested folder with files found to move.")

def find_empty_directories(base_dir):
    """
    Recursively finds and returns a list of empty directories (directories with no files or subdirectories)
    within base_dir.
    """
    empty_dirs = []
    for root, dirs, files in os.walk(base_dir):
        if not os.listdir(root):
            empty_dirs.append(root)
    return empty_dirs

def generate_empty_dir_report(empty_dirs, destination):
    """
    Generates a JSON report of empty directories.
    If the report file exists, a new file is created with a timestamp appended.
    Also, a total count is added to the report.
    """
    os.makedirs(destination, exist_ok=True)
    base_filename = "empty-directories.json"
    report_path = os.path.join(destination, base_filename)
    
    if os.path.exists(report_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_filename = f"empty-directories_{timestamp}.json"
        report_path = os.path.join(destination, base_filename)
    
    total_count = len(empty_dirs)
    report_data = {
        "total_empty_directories": total_count,
        "empty_directories": [
            {"name": os.path.basename(dir_path), "location": os.path.abspath(dir_path)}
            for dir_path in empty_dirs
        ]
    }
    
    try:
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=4)
        print(f"Empty directories report generated at: {report_path}")
    except Exception as e:
        print(f"Error generating empty directories report: {e}")

def delete_empty_directories_recursive(current_dir, base_dir):
    """
    Recursively deletes empty directories within current_dir.
    Uses post-order traversal (deepest directories first) and never deletes the base directory.
    """
    for item in os.listdir(current_dir):
        full_path = os.path.join(current_dir, item)
        if os.path.isdir(full_path):
            delete_empty_directories_recursive(full_path, base_dir)
    if current_dir != base_dir and not os.listdir(current_dir):
        try:
            os.rmdir(current_dir)
            print(f"Deleted empty directory: {current_dir}")
        except Exception as e:
            print(f"Error deleting directory {current_dir}: {e}")

def consolidate_txt_files(base_dir, destination):
    """
    Consolidates all .txt files (recursively) from base_dir into a single file.
    Only unique file contents are included.
    The consolidated file is written to the destination directory.
    Naming follows the same timestamp logic as report files.
    """
    # Scan for all .txt files under base_dir.
    files_dict = scan_files(base_dir, ext_filter=".txt")
    unique_contents = set()
    
    for file_list in files_dict.values():
        for file_path in file_list:
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            unique_contents.add(content)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    if not unique_contents:
        print("No text data found to consolidate.")
        return

    # Prepare consolidated content. Separate each unique file's content by two newlines.
    consolidated_content = "\n\n".join(unique_contents)

    os.makedirs(destination, exist_ok=True)
    base_filename = "consolidated.txt"
    consolidated_path = os.path.join(destination, base_filename)
    
    if os.path.exists(consolidated_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_filename = f"consolidated_{timestamp}.txt"
        consolidated_path = os.path.join(destination, base_filename)
    
    try:
        with open(consolidated_path, "w", encoding="utf-8") as f:
            f.write(consolidated_content)
        print(f"Consolidated file generated at: {consolidated_path}")
    except Exception as e:
        print(f"Error writing consolidated file: {e}")

def main():
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report", action="store_true", help="Generates a report of duplicate files or folders")
    group.add_argument("--move", action="store_true", help="Moves duplicate files or folders to a directory")
    group.add_argument("--move-out", action="store_true", help="Moves files (or the deepest folder) from nested directories to the current directory")
    group.add_argument("--delete", action="store_true", help="Deletes duplicate files or folders in nested directories")
    group.add_argument("--consolidate", action="store_true", help="Consolidates all .txt files into one file with unique data (only works with --type .txt)")
    group.add_argument("--help", action="store_true", help="Displays this help menu")

    parser.add_argument("--type", type=str, help="Specifies the type of item to process (e.g., file, folder, .txt, .jpg, .zip)")
    parser.add_argument("--location", type=str, help="Specifies a custom path for report, move, or consolidate (e.g., path=c:/app/xxx)")
    parser.add_argument("--name", type=str, help="Specifies a specific file or folder name to filter operations")
    parser.add_argument("--cleanup", action="store_true", help="If used with --report, generates an empty directories report only; if used with --delete, recursively deletes empty directories from the base directory")
    parser.add_argument("--search-location", type=str, help="Specifies the base directory for all operations (e.g., path=c:/app/abc or path=/opt/var/data). If not provided, the current working directory is used.")
    parser.add_argument("--all", action="store_true", help="If used with --delete, deletes ALL items of the specified type; if used with --move, moves ALL items of the specified type.")

    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)
    
    if args.cleanup and not (args.report or args.delete):
        print("Warning: The --cleanup option is only supported with --report and --delete commands. Ignoring --cleanup.")

    # Determine base directory for scanning.
    if args.search_location:
        base_dir = parse_location(args.search_location)
        if not os.path.isdir(base_dir):
            print(f"Error: Provided search location '{base_dir}' is not a valid directory.")
            sys.exit(1)
    else:
        base_dir = os.getcwd()

    ext_filter = None
    if args.type:
        type_arg = args.type.lower()
        if type_arg == "file":
            item_type = "file"
        elif type_arg == "folder":
            item_type = "folder"
        elif type_arg.startswith('.'):
            item_type = "file"
            ext_filter = type_arg
        else:
            item_type = "folder" if args.report else "file"
    else:
        item_type = "folder" if args.report else "file"

    name_filter = args.name if args.name else None

    # Determine destination directory.
    if args.report:
        if args.location:
            destination = parse_location(args.location)
        else:
            destination = os.path.join(os.getcwd(), "reports")
    elif args.consolidate:
        if args.location:
            destination = parse_location(args.location)
        else:
            destination = os.path.join(os.getcwd(), "consolidated")
    else:
        if args.location:
            destination = parse_location(args.location)
        else:
            destination = os.path.join(os.getcwd(), "duplicate")

    if args.report:
        if args.cleanup:
            empty_dirs = find_empty_directories(base_dir)
            if empty_dirs:
                generate_empty_dir_report(empty_dirs, destination)
            else:
                print("No empty directories found.")
        else:
            if item_type == "folder":
                results = scan_folders(base_dir, name_filter)
            else:
                results = scan_files(base_dir, name_filter, ext_filter)
            duplicates = {name: paths for name, paths in results.items() if len(paths) > 1}
            if duplicates:
                generate_report(duplicates, destination)
            else:
                print("No duplicates found.")
    elif args.move:
        if args.all:
            # Move ALL items of the specified type.
            if item_type == "folder":
                results = scan_folders(base_dir, name_filter)
            else:
                results = scan_files(base_dir, name_filter, ext_filter)
            if results:
                move_all_items(results, destination)
            else:
                print("No items found to move.")
        else:
            # Move duplicates only.
            if item_type == "folder":
                results = scan_folders(base_dir, name_filter)
            else:
                results = scan_files(base_dir, name_filter, ext_filter)
            duplicates = {name: paths for name, paths in results.items() if len(paths) > 1}
            if duplicates:
                move_duplicates(duplicates, destination, item_type)
            else:
                print("No duplicates found to move.")
    elif args.delete:
        if args.all:
            # Delete ALL items of the specified type.
            if item_type == "folder":
                results = scan_folders(base_dir, name_filter)
            else:
                results = scan_files(base_dir, name_filter, ext_filter)
            if results:
                delete_all_items(results, item_type)
            else:
                print("No items found to delete.")
        elif args.cleanup:
            delete_empty_directories_recursive(base_dir, base_dir)
        else:
            if item_type == "folder":
                results = scan_folders(base_dir, name_filter)
            else:
                results = scan_files(base_dir, name_filter, ext_filter)
            duplicates = {name: paths for name, paths in results.items() if len(paths) > 1}
            if duplicates:
                for name, paths in duplicates.items():
                    for path in paths[1:]:
                        if not os.path.exists(path):
                            print(f"Source not found (already moved or deleted): {path}")
                            continue
                        try:
                            if item_type == "folder":
                                shutil.rmtree(path)
                                print(f"Deleted folder: {path}")
                            else:
                                os.remove(path)
                                print(f"Deleted file: {path}")
                        except Exception as e:
                            print(f"Error deleting {path}: {e}")
            else:
                print("No duplicates found to delete.")
    elif args.move_out:
        if item_type == "folder":
            move_out_last_folder(base_dir)
        else:
            move_out_files(base_dir)
    elif args.consolidate:
        if not (args.type and args.type.lower() == ".txt"):
            print("Error: The --consolidate command only supports --type .txt.")
            print_help()
            sys.exit(1)
        consolidate_txt_files(base_dir, destination)
    else:
        print("Invalid command or option provided.")
        print_help()

if __name__ == "__main__":
    main()
