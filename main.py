import os
import platform
import re
import shutil
import subprocess
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="../../../style.css">
    <title>{title}</title>
</head>

<body>
    <div class="header">
        <div class="date">{date}</div>
        <h1>{title}</h1>
        {metrics}
    </div>
    <div class="content">
        <div class="media-grid">
{media}        </div>
        <p>{text}</p>
    </div>
</body>
</html>
"""


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
    md_output_path = os.path.join(os.getcwd(), "journals/md")
    html_output_path = os.path.join(os.getcwd(), "journals/html")
    for path in [md_output_path, html_output_path]:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
    return md_output_path, html_output_path


def convert_image(src, dest):
    subprocess.run(["magick", src, "-quality", "80", dest], check=True)
    return True


def process_entry(
    filename, entries_path, resources_path, md_output_path, html_output_path
):
    file_path = os.path.join(entries_path, filename)
    if not os.path.isfile(file_path):
        return

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
    md_entry_folder = os.path.join(md_output_path, entry_folder_name)
    html_entry_folder = os.path.join(html_output_path, entry_folder_name)
    os.makedirs(md_entry_folder, exist_ok=True)
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
            output_name = os.path.basename(link)
            output_path = os.path.join(html_entry_folder, output_name)
            shutil.copy2(src, output_path)
            converted_media.append({"type": "other", "filename": output_name})

    md_path = os.path.join(md_entry_folder, "content.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        for m in converted_media:
            if m["type"] == "heic":
                f.write(f"![]({m['avif']})\n")
            else:
                f.write(f"![]({m['filename']})\n")
        f.write(f"{text_content}\n\n")

    html_path = os.path.join(html_entry_folder, "index.html")
    media_html = ""
    for m in converted_media:
        if m["type"] == "heic":
            media_html += f"""<picture>
                <source srcset="{m["avif"]}" type="image/avif">
                <img src="{m["fallback"]}" loading="lazy">
            </picture>"""
        else:
            media_html += f'<img src="{m["filename"]}" loading="lazy">\n'
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(
            HTML_TEMPLATE.format(
                title=title,
                date=date,
                metrics=metrics_html,
                media=media_html,
                text=text_content,
            )
        )

    print(f"Created: {entry_folder_name}/content.md")
    print(f"Created: {entry_folder_name}/index.html")


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

    md_output_path, html_output_path = setup_output_folders()

    files = sorted(
        f
        for f in os.listdir(entries_path)
        if os.path.isfile(os.path.join(entries_path, f))
    )

    for filename in files:
        process_entry(
            filename, entries_path, resources_path, md_output_path, html_output_path
        )


def extract_title(html_content):
    match = re.search(r"<div class='title'>([^<]+)</div>", html_content)
    return match.group(1) if match else ""


def extract_text_content(html_content):
    match = re.search(
        r"<div class='title'[^>]*>.*?</div><div class='bodyText'>(.*?)</div>",
        html_content,
        re.DOTALL,
    )
    if not match:
        return ""
    body = match.group(1)
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def extract_activity_metrics(html_content):
    metrics = []
    pattern = r"<div class='gridItemOverlayText activityMetrics'[^>]*>([^<]+)</div>"
    matches = re.findall(pattern, html_content)
    for m in matches:
        text = m.strip()
        if text:
            metrics.append(text)
    return metrics


def extract_media_links(html_content):
    media_extensions = (
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
    pattern = r'(?:src|href)=["\']([^"\']+)["\']'
    matches = re.findall(pattern, html_content)
    links = []
    for m in matches:
        if m.lower().endswith(media_extensions):
            links.append(m.replace("../Resources/", ""))
    return links


if __name__ == "__main__":
    main()
