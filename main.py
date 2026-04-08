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

JOURNAL_HTML_TEMPLATE = """<!DOCTYPE html>
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
        <a href="../../index.html" class="back-link">← Back</a>
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

VIDEO_EXTENSIONS = (".mov", ".mp4", ".m4v")

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".heic",
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
    thumbnails_path = os.path.join(os.getcwd(), "journals", "thumbnails")
    if os.path.exists(JOURNAL_OUTPUT_PATH):
        shutil.rmtree(JOURNAL_OUTPUT_PATH)
    if os.path.exists(JOURNAL_BASE_FILE):
        os.remove(JOURNAL_BASE_FILE)
    os.makedirs(html_output_path, exist_ok=True)
    os.makedirs(thumbnails_path, exist_ok=True)
    return html_output_path, thumbnails_path


def convert_image(src, dest, size=None):
    cmd = ["magick", src, "-quality", "80"]
    if size:
        cmd.extend(
            [
                "-resize",
                f"{size}x{size}^",
                "-gravity",
                "center",
                "-extent",
                f"{size}x{size}",
            ]
        )
    cmd.append(dest)
    subprocess.run(cmd, check=True)
    return True


def generate_video_thumbnail(video_src, thumbnails_path, entry_folder_name, basename):
    frame_path = os.path.join(
        thumbnails_path, f"{entry_folder_name}_{basename}_frame.png"
    )
    avif_name = f"{entry_folder_name}_{basename}.avif"
    avif_path = os.path.join(thumbnails_path, avif_name)
    try:
        # Try to extract the first frame using ffmpeg
        subprocess.run(
            ["ffmpeg", "-i", video_src, "-frames:v", "1", "-q:v", "2", frame_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if os.path.exists(frame_path):
            convert_image(frame_path, avif_path)
            try:
                os.remove(frame_path)
            except OSError:
                pass
            return avif_name
    except Exception:
        pass
    return None


def create_thumbnail(src, dest_folder, basename, size=200):
    dest = os.path.join(dest_folder, f"{basename}.avif")
    convert_image(src, dest, size)
    return os.path.basename(dest)


def build_media_html(media_item):
    if media_item["type"] == "heic":
        return f"""<picture onclick="openLightbox('{media_item["avif"]}')">
                <source srcset="{media_item["avif"]}" type="image/avif">
                <img src="{media_item["fallback"]}" loading="lazy" onload="this.style.opacity=1">
            </picture>"""
    elif media_item["type"] == "image":
        return f'<img src="{media_item["filename"]}" loading="lazy" onload="this.style.opacity=1" onclick="openLightbox(\'{media_item["filename"]}\')">'
    elif media_item["type"] == "video":
        return f'<video src="{media_item["filename"]}" controls playsinline loading="lazy"></video>'
    return ""


def process_entry(
    filename, entries_path, resources_path, html_output_path, thumbnails_path
) -> list:
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
                thumb_name = create_thumbnail(
                    src, thumbnails_path, f"{entry_folder_name}_{basename}"
                )
                converted_media.append(
                    {
                        "type": "heic",
                        "avif": avif_name,
                        "fallback": heic_name,
                        "thumbnail": thumb_name,
                    }
                )
        elif ext in IMAGE_EXTENSIONS:
            avif_name = f"{basename}.avif"
            avif_path = os.path.join(html_entry_folder, avif_name)
            if convert_image(src, avif_path):
                thumb_name = create_thumbnail(
                    src, thumbnails_path, f"{entry_folder_name}_{basename}"
                )
                converted_media.append(
                    {"type": "image", "filename": avif_name, "thumbnail": thumb_name}
                )
        elif ext in VIDEO_EXTENSIONS:
            video_name = basename + ext
            video_path = os.path.join(html_entry_folder, video_name)
            shutil.copy2(src, video_path)
            thumb_avif = generate_video_thumbnail(
                video_path, thumbnails_path, entry_folder_name, basename
            )
            converted_media.append(
                {"type": "video", "filename": video_name, "thumbnail": thumb_avif}
            )

    html_path = os.path.join(html_entry_folder, "index.html")
    if converted_media:
        media_grid = '        <div class="media-grid">\n'
        for m in converted_media:
            media_grid += f"            {build_media_html(m)}\n"
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


def build_home_row(filename, output):
    entry_folder_name = filename.replace(".html", "")
    date = entry_folder_name[:10] if len(entry_folder_name) >= 10 else ""

    text_snippet = (
        output[0][:150] + "..." if output[0] and len(output[0]) > 150 else output[0]
    )

    thumbnails = ""
    for m in output[1][:4]:
        if m.get("thumbnail"):
            thumbnails += f'<img src="thumbnails/{m["thumbnail"]}" loading="lazy" onload="this.style.opacity=1">'

    return {
        "date": date,
        "link": f"html/{entry_folder_name}/",
        "text": text_snippet,
        "thumbnails": thumbnails,
    }


def build_home_page(rows, output_path):
    home_page_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Journals</title>
    <link rel="stylesheet" href="../../style.css">
</head>
<body>
    <h1>My Journals</h1>
    <div class="journal-list">
"""

    for row in rows[::-1]:
        home_page_html += f"""        <a href="{row["link"]}" class="journal-row">
            <div class="journal-info">
                <div class="journal-date">{row["date"]}</div>
                <div class="journal-text">{row["text"]}</div>
            </div>
            <div class="journal-thumbnails">{row["thumbnails"]}</div>
        </a>
"""

    home_page_html += """    </div>
</body></html>"""

    home_page_path = os.path.join(os.getcwd(), output_path)
    with open(home_page_path, "w", encoding="utf-8") as f:
        f.write(home_page_html)

    return home_page_path


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

    html_output_path, thumbnails_path = setup_output_folders()

    files = sorted(
        f
        for f in os.listdir(entries_path)
        if os.path.isfile(os.path.join(entries_path, f))
    )

    rows = []

    print("Processing journal entries...")

    for i, filename in enumerate(files):
        output = process_entry(
            filename, entries_path, resources_path, html_output_path, thumbnails_path
        )
        print(f"[{i + 1}/{len(files)}] {int((i + 1) / len(files) * 100)}%")
        rows.append(build_home_row(filename, output))

    build_home_page(rows, JOURNAL_BASE_FILE)

    print("All journal entries processed and home page generated.")


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
        if m.lower().endswith(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS):
            links.append(m.replace("../Resources/", ""))
    return links


if __name__ == "__main__":
    main()
