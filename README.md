# Apple Journals To Web Pages

Convert Apple Journal entries to static HTML and Markdown files.

## Requirements

```bash
pip install -r requirements.txt
```

Make sure HEIC image conversion, you need to have [ImageMagick](https://imagemagick.org/) available on your system.

## Usage

Make

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

## To-do

- [x] Fix non HEIC/AVIF image formats (basically convert all images)
- [x] Make a homepage with all the journals like on iOS
- - [x] Should we use smaller image avif thumbnails on the main page?
- [ ] Generate OpenGraph tags for every page
- [ ] Include health data in journals like steps
- [x] Add a progress bar in the Python CLI
- [x] Exporting a webpage (with all the content in the HTML, or a zip?)
- - [-] Option to include HEICs, or only AVIFs
- [ ] Allow importing .zips
