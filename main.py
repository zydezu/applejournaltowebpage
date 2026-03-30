import os
import platform
import re
import shutil
import subprocess
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

JOURNAL_BASE_FILE = "journals/index.html"
JOURNAL_OUTPUT_PATH = "journals/html"

BASE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Journals</title>
    <link rel="stylesheet" href="../../style.css">
</head>

<body>
    <div class="journals">
        {entries}
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="../../../style.css">
    <script src="../../../image.js"></script>
</head>

<body>
    <div class="header">
        <div class="date">{date}</div>
        <h1>{title}</h1>
        {metrics}
    </div>
    <div class="content">
{media_grid}
        <p>{text}</p>
    </div>
</body>
</html>
"""

MEDIA_EXTENSIONS = (
    ".heic",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".mov",
    ".mp4",
    ".m4v",
)

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
)


def main():
    open_journal_folder()


def pick_folder():
    if platform.system() == "Linux":
        try:
            result = subprocess.run(
                ["zenity", "--file-selection", "--directory"],
                stdout=subprocess.PIPE,
                text=True,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            return None
    else:
        return filedialog.askdirectory()


def find_paths(folder_path):
    entries_path = None
    resources_path = None
    for root, dirs, files in os.walk(folder_path):
        if "Entries" in dirs:
            entries_path = os.path.join(root, "Entries")
        if "Resources" in dirs:
            resources_path = os.path.join(root, "Resources")
        if entries_path and resources_path:
            break
    return entries_path, resources_path


def setup_output_folders():
    html_output_path = os.path.join(os.getcwd(), JOURNAL_OUTPUT_PATH)
    if os.path.exists(JOURNAL_OUTPUT_PATH):
        shutil.rmtree(JOURNAL_OUTPUT_PATH)
    if os.path.exists(JOURNAL_BASE_FILE):
        os.remove(JOURNAL_BASE_FILE)
    os.makedirs(html_output_path, exist_ok=True)
    return html_output_path


def convert_image(src, dest):
    subprocess.run(["magick", src, "-quality", "80", dest], check=True)
    return True


def process_entry(filename, entries_path, resources_path, html_output_path) -> list:
    file_path = os.path.join(entries_path, filename)
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    title = extract_title(content)
    text_content = extract_text_content(content)
    media_links = extract_media_links(content)
    activity_metrics = extract_activity_metrics(content)

    entry_folder_name = filename.replace(".html", "")
    date = entry_folder_name[:10] if len(entry_folder_name) >= 10 else ""

    metrics_html = ""
    for metric in activity_metrics:
        metrics_html += f'<div class="metric">{metric}</div>\n'
    html_entry_folder = os.path.join(html_output_path, entry_folder_name)
    os.makedirs(html_entry_folder, exist_ok=True)

    converted_media = []
    for link in media_links:
        src = os.path.join(resources_path, link)
        if not os.path.exists(src):
            continue
        ext = os.path.splitext(link)[1].lower()
        basename = os.path.splitext(os.path.basename(link))[0]

        if ext == ".heic":
            heic_name = f"{basename}.heic"
            heic_path = os.path.join(html_entry_folder, heic_name)
            shutil.copy2(src, heic_path)

            avif_name = f"{basename}.avif"
            avif_path = os.path.join(html_entry_folder, avif_name)
            if convert_image(src, avif_path):
                converted_media.append(
                    {"type": "heic", "avif": avif_name, "fallback": heic_name}
                )
        else:
            if ext in IMAGE_EXTENSIONS:
                avif_name = f"{basename}.avif"
                avif_path = os.path.join(html_entry_folder, avif_name)
                if convert_image(src, avif_path):
                    converted_media.append({"type": "other", "filename": avif_name})
            else:
                shutil.copy2(src, os.path.join(html_entry_folder, basename + ext))
                converted_media.append({"type": "other", "filename": basename + ext})

    html_path = os.path.join(html_entry_folder, "index.html")
    if converted_media:
        media_grid = '        <div class="media-grid">\n'
        for m in converted_media:
            if m["type"] == "heic":
                media_grid += f"""            <picture onclick="openLightbox('{m["avif"]}')">
                <source srcset="{m["avif"]}" type="image/avif">
                <img src="{m["fallback"]}" loading="lazy" onload="this.style.opacity=1">
            </picture>"""
            else:
                media_grid += f'<img src="{m["filename"]}" loading="lazy" onload="this.style.opacity=1" onclick="openLightbox(\'{m["filename"]}\')">\n'
        media_grid += "</div>\n"
    else:
        media_grid = ""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(
            HTML_TEMPLATE.format(
                title=title,
                date=date,
                metrics=metrics_html,
                media_grid=media_grid,
                text=text_content,
            )
        )

    return [text_content, converted_media]


def open_journal_folder():
    folder_path = pick_folder()
    if not folder_path:
        return

    entries_path, resources_path = find_paths(folder_path)

    if not entries_path:
        print("Error: entries folder not found")
        return

    if not resources_path:
        print("Error: Resources folder not found")
        return

    html_output_path = setup_output_folders()

    files = sorted(
        f
        for f in os.listdir(entries_path)
        if os.path.isfile(os.path.join(entries_path, f))
    )

    home_page_path = os.path.join(os.getcwd(), "journals/index.html")
    home_page_html = ""

    for i, filename in enumerate(files):
        output = process_entry(filename, entries_path, resources_path, html_output_path)
        print(f"[{i + 1}/{len(files)}] {int((i + 1) / len(files) * 100)}%")
        home_page_html += f'<a href="{html_output_path}/">{output[0]}</a><br>'

    with open(home_page_path, "w", encoding="utf-8") as f:
        f.write(home_page_html)


def extract_title(html_content):
    match = re.search(r"<div class='title'>([^<]+)</div>", html_content)
    return match.group(1) if match else ""


def extract_text_content(html_content):
    matches = re.findall(
        r"<div class='title'[^>]*>.*?</div><div class='bodyText'>(.*?)</div>",
        html_content,
        re.DOTALL,
    )
    if not matches:
        return ""
    texts = []
    for body in matches:
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        texts.append(text)
    return "<br>".join(texts).replace("…", "...")


def extract_activity_metrics(html_content):
    activities = []
    items = re.findall(
        r'<div class="gridItem[^"]*"[^>]*>.*?<div class=\'gridItemOverlayText activityType\'[^>]*>([^<]+)</div>.*?<div class=\'gridItemOverlayText activityMetrics\'[^>]*>([^<]+)</div>',
        html_content,
        re.DOTALL,
    )
    for activity_type, activity_metric in items:
        activities.append(f"{activity_type.strip()}: {activity_metric.strip()}")
    return activities


def extract_media_links(html_content):
    pattern = r'(?:src|href)=["\']([^"\']+)["\']'
    matches = re.findall(pattern, html_content)
    links = []
    for m in matches:
        if m.lower().endswith(MEDIA_EXTENSIONS):
            links.append(m.replace("../Resources/", ""))
    return links


if __name__ == "__main__":
    main()
