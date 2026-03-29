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

Select your Apple Journal folder when prompted.

## Output

The script generates two output directories in `journals/`:

- `html/` - HTML files with styling intended for viewing

## Features

- Extracts title, date, and text content from journal entries
- Converts HEIC images to AVIF with HEIC fallback, so Apple devices retain the original image quality
- Responsive grid layout with dark mode support

## To-do

- Fix non HEIC/AVIF image formats (basically convert all images)
- Make a homepage with all the journals like on iOS
- - Infact mirror more iOS design
- - Should we use smaller image avif thumbnails on the main page?
- Include health data in journals like steps
- Add a progress bar in the Python CLI
- Exporting a webpage (with all the content in the HTML, or a zip?)
- - Option to include HEICs, or only AVIFs
- Allow importing .zips
- Rewrite this to be usable from a website (eg: convert all the code to Javascript for the web)
