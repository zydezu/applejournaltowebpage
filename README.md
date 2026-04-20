# Apple Journals To Web Pages

Convert Apple Journal entries to static HTML and Markdown files.

## Requirements

```bash
pip install -r requirements.txt
```

For HEIC image conversion to work, you must have [ImageMagick](https://imagemagick.org/) installed and available on your system.

## Usage

To run the script:

```bash
python main.py
```

Select the exported Apple Journal folder when prompted. You can export Journal data on iOS devices in the Journal app and transfer it to a computer with your preferred method.

## Output

The script generates its output in the `journals/` directory:

- `html/` - HTML files with styling intended for viewing
- `thumbnails/` - thumbnails used for the home page showing a list of all the journals

## Features

- Extracts title, date, and text content from journal entries, creating clean HTML files as output
- Converts HEIC images to AVIF with HEIC fallback, so Apple devices retain the original image quality
- Responsive grid layout with dark mode support
- Optional support to upload to an r2 bucket

## R2 Bucket

To make use of an R2 bucket, for example, if uploading large files for web publication, fill in these values in a `.env` file.
```
R2_ACCOUNT_ID
R2_ACCESS_KEY
R2_SECRET_KEY
R2_BUCKET
R2_PUBLIC_URL
R2_TOKEN_VALUE
BASE_URL (optional, will default to https://example.com if not filled in)
```

## To-do

- [x] Fix non HEIC/AVIF image formats (basically convert all images)
- [x] Make a homepage with all the journals like on iOS
- - [x] Should we use smaller image avif thumbnails on the main page?
- [x] Generate OpenGraph tags for every page
- [ ] Add a h264 fallback for videos
- [ ] Include health data in journals like steps
- [x] Add a progress bar in the Python CLI
- [x] Exporting a webpage (with all the content in the HTML, or a zip?)
- - [ ] Option to include HEICs, or only AVIFs
- [ ] Allow importing Apple Journal folders as .zips
