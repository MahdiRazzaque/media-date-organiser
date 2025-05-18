import os
import shutil
import re
from datetime import datetime
import subprocess
import json
import sys
import time

use_delay = False  # Set to True to simulate delays for testing purposes
delay_time = 0.1  # Delay in seconds

def delay():
    if not use_delay:
        return
    
    time.sleep(delay_time)  # Simulate a delay for testing purposes

def get_script_dir():
    """Get the directory where the script itself is located."""
    return os.path.dirname(os.path.abspath(__file__))

def get_root_dir():
    """
    Get the root directory for media files.
    As per original logic, this is the parent of the script's directory.
    e.g., if script is in 'C:/project/scripts/', root_dir is 'C:/project/'.
    """
    return os.path.dirname(get_script_dir())

def create_folders():
    """Create required output folders in the root directory if they don't exist."""
    root_dir = get_root_dir()
    # Ensure the base 'output' directory exists first
    base_output_dir = os.path.join(root_dir, 'output')
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)
        
    folders = ['output/failed', 'output/videos', 'output/photos']
    for folder_name in folders:
        folder_path = os.path.join(root_dir, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

def count_media_files():
    """Count total number of photos and videos in root directory."""
    root_dir = get_root_dir()
    
    all_files = []
    try:
        all_files = os.listdir(root_dir)
    except FileNotFoundError:
        print(f"ERROR: The root directory for media files was not found: {root_dir}")
        print("Please ensure the script is placed in a subdirectory of your media files folder.")
        print("Expected structure: YourMediaFolder/scripts_folder/this_script.py")
        sys.exit(1)
        
    photo_count = sum(1 for f in all_files if f.lower().endswith('.jpg') and os.path.isfile(os.path.join(root_dir, f)))
    video_count = sum(1 for f in all_files if f.lower().endswith('.mp4') and os.path.isfile(os.path.join(root_dir, f)))
    
    return photo_count, video_count

def extract_date_from_filename(filename):
    """Extract date from filename in format IMG/VID/PTV-YYYYMMDD-WA#### or VID-YYYYMMDD-WA####."""
    pattern = r'(?:IMG|VID|PTV)-(\d{4})(\d{2})(\d{2})-WA\d+'
    match = re.match(pattern, filename)
    if match:
        year, month, day = match.groups()
        try:
            return datetime.strptime(f"{year}-{month}-{day} 15:00:00", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return None

def get_file_metadata(filepath):
    """Get metadata using exiftool."""
    try:
        script_dir = get_script_dir()
        exiftool_path = os.path.join(script_dir, 'exiftool.exe')
        result = subprocess.run([exiftool_path, '-json', filepath], 
                              capture_output=True, text=True, check=True, encoding='utf-8')
        # Exiftool can sometimes return an array of an array for a single file.
        output_data = json.loads(result.stdout)
        if isinstance(output_data, list) and len(output_data) > 0:
            metadata = output_data[0]
            if isinstance(metadata, list) and len(metadata) > 0: # Handle [[{...}]]
                 metadata = metadata[0]
            return metadata
        return None # Or handle as an error
    except subprocess.CalledProcessError as e:
        # ExifTool ran but returned an error (e.g., file not supported, corrupted)
        error_output = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        # print(f"ExifTool error processing {os.path.basename(filepath)}: {error_output.strip()}") # Verbose
        return None # Let the calling function decide how to log this
    except FileNotFoundError:
        # This specific catch should ideally not be hit if main() check for exiftool.exe works
        print(f"CRITICAL ERROR: exiftool.exe not found at {exiftool_path} during metadata extraction.")
        print("The script should have exited earlier. Please report this bug.")
        sys.exit(1) # Should not happen if initial check is in place
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from ExifTool for {os.path.basename(filepath)}: {e}")
        print(f"ExifTool output was: {result.stdout[:500]}...") # Log part of the output
        return None
    except Exception as e:
        # Catch-all for other unexpected errors during ExifTool interaction
        print(f"Unexpected error getting metadata for {os.path.basename(filepath)} with ExifTool: {e}")
        return None


def set_file_dates(filepath, target_date):
    """Set file creation and modification dates using exiftool."""
    date_str = target_date.strftime("%Y:%m:%d %H:%M:%S")
    try:
        script_dir = get_script_dir()
        exiftool_path = os.path.join(script_dir, 'exiftool.exe')
        common_args = [
            exiftool_path,
            '-overwrite_original' # Be cautious: this modifies files in-place!
        ]
        
        if filepath.lower().endswith('.mp4'):
            specific_args = [
                f'-CreateDate={date_str}',
                f'-ModifyDate={date_str}',
                f'-MediaCreateDate={date_str}',
                f'-MediaModifyDate={date_str}',
                f'-TrackCreateDate={date_str}',
                f'-TrackModifyDate={date_str}',
                f'-FileCreateDate={date_str}', # System field, can be tricky
                f'-FileModifyDate={date_str}'  # System field
            ]
        else: # For photos (.jpg)
            specific_args = [
                f'-AllDates={date_str}', # Sets DateTimeOriginal, CreateDate, ModifyDate
                f'-FileModifyDate={date_str}', # System field
            ]
        
        command = common_args + specific_args + [filepath]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        # print(f"Successfully set dates for {os.path.basename(filepath)}. Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        print(f"ExifTool error setting dates for {os.path.basename(filepath)}: {error_output.strip()}")
        return False
    except FileNotFoundError:
        # This specific catch should ideally not be hit if main() check for exiftool.exe works
        print(f"CRITICAL ERROR: exiftool.exe not found at {exiftool_path} during date setting.")
        sys.exit(1) # Should not happen
    except Exception as e:
        print(f"Unexpected error setting dates for {os.path.basename(filepath)} with ExifTool: {e}")
        return False

def process_files(total_photos_at_start, total_videos_at_start):
    """Main function to process files."""
    root_dir = get_root_dir()
    
    photo_counter = 0
    video_counter = 0
    
    results = {
        'successful': [],
        'failed': [],
        'total_processed': 0,
        'total_success': 0,
        'total_failed': 0,
        'processed_photos': 0,
        'processed_videos': 0,
        'failed_photos': 0,
        'failed_videos': 0,
        'skipped_already_in_output': 0
    }
    
    output_photos_dir = os.path.join(root_dir, 'output', 'photos')
    output_videos_dir = os.path.join(root_dir, 'output', 'videos')
    output_failed_dir = os.path.join(root_dir, 'output', 'failed')

    # Process photos first
    print("\nProcessing photos...")
    # Get a static list of files to iterate over to avoid issues with moving files
    files_in_root = [f for f in os.listdir(root_dir) if os.path.isfile(os.path.join(root_dir, f))]

    for filename in files_in_root:
        delay()
        if not filename.lower().endswith('.jpg'):
            continue

        photo_counter += 1
        filepath = os.path.join(root_dir, filename)
        
        # Check if file already exists in target or failed folders (simple check)
        if os.path.exists(os.path.join(output_photos_dir, filename)) or \
           os.path.exists(os.path.join(output_failed_dir, filename)):
            print(f"[Skipped files: {results['skipped_already_in_output']-1}]: Skipping {filename}, already found in an output folder.", end='\r')
            results['skipped_already_in_output'] += 1
            continue

        results['total_processed'] += 1
        success = False
        error_message = "Unknown error" # Default error message

        try:
            date = extract_date_from_filename(os.path.splitext(filename)[0])
            
            if date is None:
                metadata = get_file_metadata(filepath)
                if metadata:
                    date_fields = ['DateTimeOriginal', 'CreateDate', 'SubSecDateTimeOriginal', 'SubSecCreateDate', 'SubSecModifyDate', 'ModifyDate', 'FileModifyDate'] # Ordered by preference
                    for field in date_fields:
                        if field in metadata and metadata[field]:
                            try:
                                # Handle various date string formats, remove timezone, fractional seconds
                                date_str_raw = str(metadata[field])
                                date_str_parts = date_str_raw.split('.')[0] # Remove fractional seconds
                                date_str_clean = date_str_parts.split('+')[0].split('-')[0].split('Z')[0].strip() # Remove timezone
                                
                                # Try common formats
                                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                                    try:
                                        date = datetime.strptime(date_str_clean, fmt)
                                        date = date.replace(hour=15, minute=0, second=0, microsecond=0)
                                        break # Date parsed successfully
                                    except ValueError:
                                        continue
                                if date: break # Found date from metadata
                            except Exception: # Broad catch for parsing unusual date strings
                                continue # Try next field
                else: # Metadata could not be read
                    error_message = "Failed to read metadata (ExifTool)"


            if date:
                if set_file_dates(filepath, date):
                    shutil.move(filepath, os.path.join(output_photos_dir, filename))
                    success = True
                else:
                    error_message = "Failed to set metadata dates (ExifTool)"
            elif not error_message or error_message == "Unknown error": # If no date and no prior error
                error_message = "Could not determine date from filename or metadata"

        except FileNotFoundError: # This would be if the source filepath is not found during processing
            error_message = f"Source file {filename} not found during processing (moved or deleted?)"
        except Exception as e:
            error_message = f"Unexpected processing error: {str(e)}"

        if success:
            results['successful'].append(filename)
            results['total_success'] += 1
            results['processed_photos'] += 1
        else:
            results['failed'].append((filename, error_message))
            results['total_failed'] += 1
            results['failed_photos'] += 1
            try:
                if os.path.exists(filepath): # Check if file still exists before moving
                    shutil.move(filepath, os.path.join(output_failed_dir, filename))
            except Exception as e_move:
                print(f"Error moving failed file {filename} to 'failed' folder: {e_move}")
        
        print(f"Photos: {photo_counter}/{total_photos_at_start} processed ({results['failed_photos']} failed, {results['skipped_already_in_output']} skipped)", end='\r')

    print()

    # Process videos second
    print("\nProcessing videos...")
    # Re-fetch or use the static list, ensuring we only process files still in root_dir
    files_in_root_for_videos = [f for f in os.listdir(root_dir) if os.path.isfile(os.path.join(root_dir, f))]

    for filename in files_in_root_for_videos:
        delay()
        if not filename.lower().endswith('.mp4'):
            continue

        video_counter += 1
        filepath = os.path.join(root_dir, filename)

        if os.path.exists(os.path.join(output_videos_dir, filename)) or \
           os.path.exists(os.path.join(output_failed_dir, filename)):
            print(f"[Skipped files: {results['skipped_already_in_output']-1}]: Skipping {filename}, already found in an output folder.", end='\r')
            results['skipped_already_in_output'] += 1
            continue
            
        results['total_processed'] += 1
        success = False
        error_message = "Unknown error"

        try:
            date = extract_date_from_filename(os.path.splitext(filename)[0])
            
            if date is None:
                metadata = get_file_metadata(filepath)
                if metadata:
                    date_fields = ['CreationDate', 'DateTimeOriginal', 'CreateDate', 'MediaCreateDate', 'TrackCreateDate', 'ModifyDate', 'MediaModifyDate', 'TrackModifyDate', 'FileModifyDate']
                    for field in date_fields:
                        if field in metadata and metadata[field]:
                            try:
                                date_str_raw = str(metadata[field])
                                date_str_parts = date_str_raw.split('.')[0] 
                                date_str_clean = date_str_parts.split('+')[0].split('-')[0].split('Z')[0].strip()
                                
                                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%SZ"): # Added Z for UTC
                                    try:
                                        date = datetime.strptime(date_str_clean, fmt)
                                        date = date.replace(hour=15, minute=0, second=0, microsecond=0)
                                        break
                                    except ValueError:
                                        continue
                                if date: break
                            except Exception:
                                continue
                else:
                    error_message = "Failed to read metadata (ExifTool)"


            if date:
                if set_file_dates(filepath, date):
                    shutil.move(filepath, os.path.join(output_videos_dir, filename))
                    success = True
                else:
                    error_message = "Failed to set metadata dates (ExifTool)"
            elif not error_message or error_message == "Unknown error":
                error_message = "Could not determine date from filename or metadata"

        except FileNotFoundError:
             error_message = f"Source file {filename} not found during processing (moved or deleted?)"
        except Exception as e:
            error_message = f"Unexpected processing error: {str(e)}"

        if success:
            results['successful'].append(filename)
            results['total_success'] += 1
            results['processed_videos'] += 1
        else:
            results['failed'].append((filename, error_message))
            results['total_failed'] += 1
            results['failed_videos'] += 1
            try:
                if os.path.exists(filepath):
                    shutil.move(filepath, os.path.join(output_failed_dir, filename))
            except Exception as e_move:
                print(f"Error moving failed file {filename} to 'failed' folder: {e_move}")
        
        print(f"Videos: {video_counter}/{total_videos_at_start} processed ({results['failed_videos']} failed, {results['skipped_already_in_output']} skipped)", end='\r')
    
    print() 
    return results

def write_summary(results):
    """Write processing summary to file."""
    root_dir = get_root_dir()
    summary_path = os.path.join(root_dir, 'output', 'summary.txt')
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("File Processing Summary\n")
            f.write("=====================\n\n")
            f.write(f"Total files considered for processing (initial scan): {results.get('initial_photos',0) + results.get('initial_videos',0)}\n")
            f.write(f"Files skipped (already in output/failed folders): {results.get('skipped_already_in_output', 0)}\n")
            f.write(f"Total files attempted for processing: {results['total_processed']}\n")
            f.write(f"Successfully processed: {results['total_success']}\n")
            f.write(f"Failed: {results['total_failed']}\n\n")
            
            f.write(f"Photos processed: {results['processed_photos']} (Failed: {results['failed_photos']})\n")
            f.write(f"Videos processed: {results['processed_videos']} (Failed: {results['failed_videos']})\n\n")

            if results['successful']:
                f.write("\nSuccessfully Processed Files:\n")
                f.write("---------------------------\n")
                for filename in results['successful']:
                    f.write(f"[OK] {filename}\n")

            if results['failed']:
                f.write("\nFailed Files:\n")
                f.write("-------------\n")
                for filename, error in results['failed']:
                    f.write(f"[X] {filename}: {error}\n")
    except Exception as e:
        print(f"ERROR: Could not write summary file to {summary_path}: {e}")

def main():
    script_dir = get_script_dir()
    root_dir = get_root_dir() # Parent of script_dir, for media files

    print("------------------------------------------")
    print("Media File Date Organizer using ExifTool")
    print("-------------------------------------------")
    print(f"Script directory:     {script_dir}")
    print(f"Media root directory: {root_dir}")

    # --- Check for ExifTool dependencies ---
    exiftool_exe_path = os.path.join(script_dir, 'exiftool.exe')
    exiftool_files_dir_path = os.path.join(script_dir, 'exiftool_files')

    all_dependencies_met = True
    missing_dependency_messages = []

    # Check for exiftool.exe
    line_len_exe = len(exiftool_exe_path) + 30
    print("\n" + line_len_exe * "-")
    print(f"Checking for 'exiftool.exe' at: {exiftool_exe_path}")
    print(line_len_exe * "-")

    if not os.path.isfile(exiftool_exe_path):
        missing_dependency_messages.append(
            f"- Required file 'exiftool.exe' not found or is not a file."
        )
        all_dependencies_met = False
        # Print immediate feedback for this specific check if missing
        print(f"  [FAIL] 'exiftool.exe' not found at the specified path.")
    else:
        print("  [OK] 'exiftool.exe' found.")

    # Check for exiftool_files folder
    line_len_files_dir = len(exiftool_files_dir_path) + 41
    print("\n" + line_len_files_dir * "-")
    print(f"Checking for 'exiftool_files' folder at: {exiftool_files_dir_path}")
    print(line_len_files_dir * "-")

    if not os.path.isdir(exiftool_files_dir_path):
        missing_dependency_messages.append(
            f"- Required folder 'exiftool_files' not found or is not a directory."
        )
        all_dependencies_met = False
        print(f"  [FAIL] 'exiftool_files' folder not found at the specified path.")
    else:
        # Check if the exiftool_files folder is empty
        try:
            if not os.listdir(exiftool_files_dir_path):
                missing_dependency_messages.append(
                    f"- Required folder 'exiftool_files' exists but is empty."
                )
                all_dependencies_met = False
                print(f"  [FAIL] 'exiftool_files' folder exists but is empty. It should contain necessary ExifTool libraries.")
            else:
                print("  [OK] 'exiftool_files' folder found and is not empty.")
        except OSError as e: # Handle potential permission errors when listing directory
            missing_dependency_messages.append(
                f"- Error accessing contents of 'exiftool_files' folder: {e}"
            )
            all_dependencies_met = False
            print(f"  [FAIL] Could not verify contents of 'exiftool_files' folder due to an error: {e}")

    if not all_dependencies_met:
        print("\n------------------------------------------------------------------------")
        print("FATAL ERROR: Essential ExifTool components are missing or misconfigured.")
        print("Script cannot continue.")
        print("------------------------------------------------------------------------")
        print("Missing components:")
        for msg in missing_dependency_messages:
            print(f"  {msg}")
        
        print("\nPlease ensure ExifTool (Windows Executable version) is correctly set up in the script directory:")
        print(f"  Your script directory: {script_dir}")
        
        print("\nInstructions:")
        print("1. Download the 'Windows Executable' zip file from the official ExifTool website:")
        print("   https://exiftool.org/")
        
        print("\n2. Unzip the downloaded file. You will typically find:")
        print("   - An executable file, often named 'exiftool(-k).exe'.")
        print("   - A folder named 'exiftool_files'.")
        
        print("\n3. Prepare the components for this script:")
        print("   a) Rename the executable: Change 'exiftool(-k).exe' (or similar) to 'exiftool.exe'.")
        print("   b) Place BOTH 'exiftool.exe' AND the 'exiftool_files' folder directly into your script directory shown above.")
        
        print("\nImportant Note:")
        print("   If you move 'exiftool.exe' to a new location (like your script directory),")
        print("   you MUST ALSO MOVE the 'exiftool_files' folder to that same location.")
        print("   These two components must be kept together for ExifTool to function correctly.")
        sys.exit(1)
    else:
        print("\n--------------------------------------------------------------------------------------------------")
        print("All required ExifTool components ('exiftool.exe' and 'exiftool_files' folder) found. Proceeding...")
        print("--------------------------------------------------------------------------------------------------")
    

    # --- Setup output folders ---
    print("\nEnsuring output folders exist...")
    create_folders() # Creates 'output/failed', 'output/photos', 'output/videos' in root_dir

    # --- Count initial files ---
    print(f"\nCounting media files in media root directory: {root_dir}")
    initial_photos, initial_videos = count_media_files()
    print(f"Found {initial_photos} photos (.jpg) and {initial_videos} videos (.mp4) to potentially process.")
    
    if initial_photos == 0 and initial_videos == 0:
        print("\nNo media files (.jpg, .mp4) found in the media root directory to process. Exiting.")
        summary_path = os.path.join(root_dir, 'output', 'summary.txt')
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("File Processing Summary\n")
                f.write("=====================\n\n")
                f.write("No media files (.jpg, .mp4) found in the media root directory to process.\n")
                f.write(f"Searched in: {root_dir}\n")
            print(f"Empty summary written to {summary_path}")
        except Exception as e:
            print(f"ERROR: Could not write empty summary file: {e}")
        sys.exit(0)

    # --- Process files ---
    print("\nStarting file processing...")
    results = process_files(initial_photos, initial_videos) # Pass initial counts
    results['initial_photos'] = initial_photos # Add to results for summary
    results['initial_videos'] = initial_videos # Add to results for summary

    # --- Write summary ---
    print("\nWriting summary report...")
    write_summary(results)
    
    print("\n--------------------")
    print("Processing Complete!")
    print("--------------------")
    print(f"Summary report written to: {os.path.join(root_dir, 'output', 'summary.txt')}")
    print(f"\nSuccessfully processed: {results['total_success']} files.")
    print(f"Photos: {results['processed_photos']} successful / {results['failed_photos']} failed (out of {initial_photos} initial .jpg files).")
    print(f"Videos: {results['processed_videos']} successful / {results['failed_videos']} failed (out of {initial_videos} initial .mp4 files).")
    if results.get('skipped_already_in_output',0) > 0:
        print(f"Skipped: {results['skipped_already_in_output']} files (already in output/failed folders).")
    print(f"Total failures: {results['total_failed']}.")


if __name__ == "__main__":
    main()