import os
import shutil
import re
from datetime import datetime
import subprocess
import json

def create_folders():
    """Create required folders if they don't exist."""
    folders = ['output/failed', 'output/videos', 'output/photos']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

def count_media_files():
    """Count total number of photos and videos in current directory."""
    photo_count = sum(1 for f in os.listdir('.') if f.lower().endswith('.jpg'))
    video_count = sum(1 for f in os.listdir('.') if f.lower().endswith('.mp4'))
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
        # Use exiftool from the program directory
        exiftool_path = os.path.join('program', 'exiftool.exe')
        result = subprocess.run([exiftool_path, '-json', filepath], 
                              capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)[0]
        return metadata
    except Exception as e:
        return None

def set_file_dates(filepath, target_date):
    """Set file creation and modification dates using exiftool."""
    date_str = target_date.strftime("%Y:%m:%d %H:%M:%S")
    try:
        # Use exiftool from the program directory
        exiftool_path = os.path.join('program', 'exiftool.exe')
        if filepath.lower().endswith('.mp4'):
            # For video files, we need to set more specific tags
            subprocess.run([
                exiftool_path,
                '-overwrite_original',
                f'-CreateDate={date_str}',
                f'-ModifyDate={date_str}',
                f'-MediaCreateDate={date_str}',
                f'-MediaModifyDate={date_str}',
                f'-TrackCreateDate={date_str}',
                f'-TrackModifyDate={date_str}',
                f'-FileCreateDate={date_str}',
                f'-FileModifyDate={date_str}',
                filepath
            ], check=True, capture_output=True)
        else:
            # For photos, use AllDates
            subprocess.run([
                exiftool_path,
                '-overwrite_original',
                f'-AllDates={date_str}',
                filepath
            ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ExifTool error: {e.stderr.decode() if e.stderr else str(e)}")
        return False

def process_files():
    """Main function to process files."""
    create_folders()
    
    # Count total files before processing
    total_photos, total_videos = count_media_files()
    
    # Initialize counters
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
        'failed_videos': 0
    }

    # Process photos first
    print("\nProcessing photos...")
    for filename in os.listdir('.'):
        if not filename.lower().endswith('.jpg'):
            continue

        photo_counter += 1
        results['total_processed'] += 1
        filepath = os.path.join('.', filename)
        success = False
        error_message = ""

        try:
            # First try to get date from filename
            date = extract_date_from_filename(os.path.splitext(filename)[0])
            
            # If filename parsing failed, try to get from metadata
            if date is None:
                metadata = get_file_metadata(filepath)
                if metadata:
                    # Try different date fields
                    date_fields = ['CreateDate', 'DateTimeOriginal', 'FileModifyDate']
                    for field in date_fields:
                        if field in metadata:
                            try:
                                date_str = metadata[field].split('+')[0].strip()  # Remove timezone if present
                                date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                                date = date.replace(hour=15, minute=0, second=0)  # Set to 3 PM
                                break
                            except ValueError:
                                continue

            if date:
                # Set the metadata dates
                if set_file_dates(filepath, date):
                    # Move file to photos folder
                    shutil.move(filepath, os.path.join('output', 'photos', filename))
                    success = True
                else:
                    error_message = "Failed to set metadata"
            else:
                error_message = "Could not determine date"

        except Exception as e:
            error_message = str(e)

        # Record results and show progress for photos
        if success:
            results['successful'].append(filename)
            results['total_success'] += 1
            results['processed_photos'] += 1
        else:
            results['failed'].append((filename, error_message))
            results['total_failed'] += 1
            results['failed_photos'] += 1
            try:
                shutil.move(filepath, os.path.join('output', 'failed', filename))
            except Exception as e:
                print(f"Error moving failed file {filename}: {e}")
        
        print(f"Photos: {photo_counter}/{total_photos} processed ({results['failed_photos']} failed)", end='\r')

    print("\nProcessing videos...")
    # Process videos second
    for filename in os.listdir('.'):
        if not filename.lower().endswith('.mp4'):
            continue

        video_counter += 1
        results['total_processed'] += 1
        filepath = os.path.join('.', filename)
        success = False
        error_message = ""

        try:
            # First try to get date from filename
            date = extract_date_from_filename(os.path.splitext(filename)[0])
            
            # If filename parsing failed, try to get from metadata
            if date is None:
                metadata = get_file_metadata(filepath)
                if metadata:
                    # Try different date fields
                    date_fields = ['CreateDate', 'DateTimeOriginal', 'FileModifyDate']
                    for field in date_fields:
                        if field in metadata:
                            try:
                                date_str = metadata[field].split('+')[0].strip()  # Remove timezone if present
                                date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                                date = date.replace(hour=15, minute=0, second=0)  # Set to 3 PM
                                break
                            except ValueError:
                                continue

            if date:
                # Set the metadata dates
                if set_file_dates(filepath, date):
                    # Move file to videos folder
                    shutil.move(filepath, os.path.join('output', 'videos', filename))
                    success = True
                else:
                    error_message = "Failed to set metadata"
            else:
                error_message = "Could not determine date"

        except Exception as e:
            error_message = str(e)

        # Record results and show progress for videos
        if success:
            results['successful'].append(filename)
            results['total_success'] += 1
            results['processed_videos'] += 1
        else:
            results['failed'].append((filename, error_message))
            results['total_failed'] += 1
            results['failed_videos'] += 1
            try:
                shutil.move(filepath, os.path.join('output', 'failed', filename))
            except Exception as e:
                print(f"Error moving failed file {filename}: {e}")
        
        print(f"Videos: {video_counter}/{total_videos} processed ({results['failed_videos']} failed)", end='\r')

    print("\n")  # Add a newline for cleaner output
    return results

def write_summary(results):
    """Write processing summary to file."""
    with open(os.path.join('output', 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write("File Processing Summary\n")
        f.write("=====================\n\n")
        f.write(f"Total files processed: {results['total_processed']}\n")
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

def main():
    # Create output directory if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')

    print("Starting file processing...")
    total_photos, total_videos = count_media_files()
    print(f"Found {total_photos} photos and {total_videos} videos to process")
    results = process_files()
    write_summary(results)
    print(f"\nProcessing complete. Check output/summary.txt for details.")
    print(f"Photos: {results['processed_photos']}/{total_photos} processed ({results['failed_photos']} failed)")
    print(f"Videos: {results['processed_videos']}/{total_videos} processed ({results['failed_videos']} failed)")

if __name__ == "__main__":
    main() 