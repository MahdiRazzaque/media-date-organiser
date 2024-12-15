# Media Date Organiser

A Python script that organises media files (photos and videos) by extracting dates from filenames or metadata, setting the correct file dates, and sorting them into appropriate folders.

## Features

- Extracts dates from filenames and metadata
- Sets correct creation and modification dates for media files
- Organises files into separate folders for photos and videos
- Handles failed files separately
- Generates a detailed summary report
- Works with both photos (.jpg) and videos (.mp4)

## Requirements

- Python 3.x
- ExifTool (for metadata manipulation)

## Setup

1. Download and install Python 3.x from [python.org](https://python.org)
2. Download ExifTool:
   - Go to [ExifTool's official website](https://exiftool.org)
   - Download the Windows Executable (ZIP file)
   - Extract the contents
   - Rename `exiftool(-k).exe` to `exiftool.exe`
   - Place `exiftool.exe` and the `exiftool_files` directory in the `program` folder

## Usage

1. Place your media files in the root directory (where the `program` folder is)
2. Make sure `exiftool.exe` and `exiftool_files` are in the `program` folder
3. Run the script:
```bash
python program/media-date-organiser.py
```

The script will:
1. Create an `output` folder with subfolders: `photos`, `videos`, and `failed`
2. Process all media files in the root directory
3. Set correct dates based on filename or metadata
4. Move files to appropriate folders in `output`
5. Generate a `summary.txt` file in the `output` folder

## Folder Structure

```
├── program/                # Program files
│   ├── exiftool.exe       # ExifTool executable
│   ├── exiftool_files/    # ExifTool supporting files
│   └── media-date-organiser.py  # Main script
│
├── output/                # Generated folders
│   ├── photos/           # Successfully processed photos
│   ├── videos/           # Successfully processed videos
│   ├── failed/           # Files that couldn't be processed
│   └── summary.txt       # Processing report
│
├── .gitignore            # Git configuration
├── .gitattributes        # Git configuration
├── README.md             # This file
└── *.jpg/*.mp4           # Your media files go here
```

## Supported Formats

- Photos: .jpg
- Videos: .mp4

## Date Extraction

The script attempts to extract dates in the following order:
1. From filename (format: XXX-YYYYMMDD-*)
2. From file metadata (various standard date fields)

All dates are set to 3 PM (15:00) on the extracted date.

## Summary Report

The generated `output/summary.txt` includes:
- Total number of files processed
- Number of successful/failed operations
- Separate counts for photos and videos
- List of all processed files with status
- Error messages for failed files

## Error Handling

Files that can't be processed (due to invalid dates, metadata issues, etc.) are:
- Moved to the `output/failed` folder
- Listed in the summary report with error details
- Counted in the failed files statistics