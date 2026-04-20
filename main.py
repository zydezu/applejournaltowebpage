import os
import platform
import re
import shutil
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from tkinter import Tk, filedialog

from r2_config import BASE_URL, R2_PUBLIC_URL, USE_R2, upload_to_r2

root = Tk()
root.withdraw()

JOURNAL_BASE_FILE = "journals/index.html"
JOURNAL_OUTPUT_PATH = "journals/html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="../../style.css">
    <link rel="icon" href="../../favicon.jpg">

    <meta property="og:title" content="{og_title}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{url}">
    <meta property="og:description" content="{description}">
    {og_image}
    <meta property="og:logo" content="{base_url}/favicon.jpg">
    <meta content="#dfa0a9" name="theme-color" />

    <meta content="summary_large_image" name="twitter:card" />

    <script src="../../image.js"></script>
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


# Image conversion
def convert_image(src: str, dest: str, size: int | None = None) -> bool:
    cmd = ["magick", src, "-quality", "80"]
    if size:
        cmd += [
            "-resize",
            f"{size}x{size}^",
            "-gravity",
            "center",
            "-extent",
            f"{size}x{size}",
        ]
    cmd.append(dest)
    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        print(f"magick error ({src}): {e}", file=sys.stderr)
        return False


def convert_image_and_thumbnail(
    src: str,
    dest_avif: str,
    thumb_avif: str,
    thumb_size: int = 200,
) -> bool:
    ok1 = convert_image(src, dest_avif)
    ok2 = convert_image(src, thumb_avif, thumb_size)
    return ok1 and ok2


# Video thumbnail
def generate_video_thumbnail(
    video_src: str,
    thumbnails_path: str,
    entry_folder_name: str,
    basename: str,
    size: int = 200,
) -> str | None:
    avif_name = f"{entry_folder_name}_{basename}.avif"
    avif_path = os.path.join(thumbnails_path, avif_name)
    tmp_png = avif_path + "_tmp.png"
    try:
        ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-i",
                video_src,
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        frame_bytes, _ = ffmpeg.communicate()
        if not frame_bytes:
            return None
        with open(tmp_png, "wb") as f:
            f.write(frame_bytes)
        convert_image(tmp_png, avif_path, size)
        try:
            os.remove(tmp_png)
        except OSError:
            pass
        return avif_name
    except Exception as e:
        print(f"video thumbnail error ({video_src}): {e}", file=sys.stderr)
        return None


# Helpers
def sanitize_filename(name: str) -> str:
    name = "".join(c for c in name if c.isalnum() or c in "-_")
    name = re.sub(r"[-_]{2,}", "_", name)  # collapse runs left by stripped unicode
    return name.strip("-_") or "untitled"


def build_media_html(media_item: dict) -> str:
    filename = media_item["filename"]
    if media_item["type"] == "image":
        return (
            f'<img src="{filename}" loading="lazy" '
            f'onload="this.style.opacity=1" '
            f"onclick=\"openLightbox('{filename}')\">"
        )
    if media_item["type"] == "video":
        return f'<video src="{filename}" controls playsinline loading="lazy"></video>'
    return ""


# HTML parsing
def extract_all(html_content: str) -> tuple[str, str, list[str], list[str]]:
    # title
    title_m = re.search(r"<div class='title'>([^<]+)</div>", html_content)
    title = title_m.group(1) if title_m else ""

    # body text
    body_matches = re.findall(
        r"<div class='title'[^>]*>.*?</div><div class='bodyText'>(.*?)</div>",
        html_content,
        re.DOTALL,
    )
    texts = []
    for body in body_matches:
        text = re.sub(r"<p[^>]*>", "\n", body)
        text = re.sub(r"</p>", "", text)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        text = "\n".join(line.strip() for line in text.split("\n"))
        texts.append(text.strip())
    combined = "<br><br>".join(texts)
    combined = combined.replace("\n", "<br>").replace("…", "...")

    # media links
    raw_links = re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html_content)
    media_links = [
        m.replace("../Resources/", "")
        for m in raw_links
        if m.lower().endswith(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)
    ]

    # activity metrics
    items = re.findall(
        r'<div class="gridItem[^"]*"[^>]*>.*?'
        r"<div class=\'gridItemOverlayText activityType\'[^>]*>([^<]+)</div>.*?"
        r"<div class=\'gridItemOverlayText activityMetrics\'[^>]*>([^<]+)</div>",
        html_content,
        re.DOTALL,
    )
    activity_metrics = [f"{t.strip()}: {m.strip()}" for t, m in items]

    return title, combined, media_links, activity_metrics


# Entry processor (runs in worker process)
def process_entry(
    filename: str,
    entries_path: str,
    resources_path: str,
    html_output_path: str,
    thumbnails_path: str,
) -> list:
    file_path = os.path.join(entries_path, filename)
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    title, text_content, media_links, activity_metrics = extract_all(content)

    entry_folder_name = sanitize_filename(filename.replace(".html", ""))
    date = entry_folder_name[:10] if len(entry_folder_name) >= 10 else ""
    page_url = f"{BASE_URL}/html/{entry_folder_name}/"

    metrics_html = "".join(f'<div class="metric">{m}</div>\n' for m in activity_metrics)

    html_entry_folder = os.path.join(html_output_path, entry_folder_name)
    os.makedirs(html_entry_folder, exist_ok=True)

    converted_media: list[dict] = []
    large_files_to_upload: list[tuple[str, str]] = []

    for link in media_links:
        src = os.path.join(resources_path, link)
        if not os.path.exists(src):
            continue

        ext = os.path.splitext(link)[1].lower()
        basename = sanitize_filename(os.path.splitext(os.path.basename(link))[0])
        if ext == ".heic":
            ext = ".avif"

        is_image = ext in IMAGE_EXTENSIONS
        is_video = ext in VIDEO_EXTENSIONS

        # large file → R2
        if USE_R2 and os.path.getsize(src) > 25 * 1024 * 1024:
            r2_key = f"journals/{entry_folder_name}/{basename}{ext}"
            large_files_to_upload.append((src, r2_key))
            r2_url = f"{R2_PUBLIC_URL.rstrip('/')}/{r2_key}"
            media_type = "image" if is_image else "video" if is_video else None
            if media_type:
                converted_media.append(
                    {"type": media_type, "filename": r2_url, "thumbnail": None}
                )
            continue

        if is_image:
            avif_name = f"{basename}.avif"
            avif_path = os.path.join(html_entry_folder, avif_name)
            thumb_name = f"{entry_folder_name}_{basename}.avif"
            thumb_path = os.path.join(thumbnails_path, thumb_name)
            if convert_image_and_thumbnail(src, avif_path, thumb_path):
                converted_media.append(
                    {"type": "image", "filename": avif_name, "thumbnail": thumb_name}
                )

        elif is_video:
            video_name = basename + ext
            video_path = os.path.join(html_entry_folder, video_name)
            shutil.copy2(src, video_path)
            thumb_avif = generate_video_thumbnail(
                video_path, thumbnails_path, entry_folder_name, basename
            )
            converted_media.append(
                {"type": "video", "filename": video_name, "thumbnail": thumb_avif}
            )

    # write entry HTML
    first_image = None
    media_grid = ""
    if converted_media:
        media_grid = '        <div class="media-grid">\n'
        for m in converted_media:
            media_grid += f"            {build_media_html(m)}\n"
            if not first_image and m.get("filename"):
                first_image = (
                    m["filename"]
                    if m["filename"].startswith("http")
                    else f"{BASE_URL}/html/{entry_folder_name}/{m['filename']}"
                )
        media_grid += "        </div>\n"

    og_image_html = (
        f'<meta property="og:image" content="{first_image}">' if first_image else ""
    )

    html_path = os.path.join(html_entry_folder, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(
            HTML_TEMPLATE.format(
                title=title,
                date=date,
                metrics=metrics_html,
                media_grid=media_grid,
                text=text_content,
                url=page_url,
                description=text_content[:200] if text_content else "",
                og_title=title if title else BASE_URL,
                og_image=og_image_html,
                base_url=BASE_URL,
            )
        )

    return [text_content, converted_media, large_files_to_upload]


# Home page
def build_home_row(filename: str, output: list, layout_class: str) -> dict:
    entry_folder_name = sanitize_filename(filename.replace(".html", ""))
    date = entry_folder_name[:10] if len(entry_folder_name) >= 10 else ""

    raw_text = re.sub(r"<[^>]+>", " ", output[0] or "")
    raw_text = re.sub(r"\s+", " ", raw_text).strip()
    text_snippet = (raw_text[:150] + "...") if len(raw_text) > 150 else raw_text

    thumbnails = ""
    for m in output[1][:4]:
        if m.get("thumbnail"):
            thumbnails += (
                f'<img src="thumbnails/{m["thumbnail"]}" loading="lazy" '
                f'onload="this.style.opacity=1">'
            )

    return {
        "date": date,
        "link": f"html/{entry_folder_name}/",
        "text": text_snippet,
        "thumbnails": thumbnails,
        "layout": layout_class,
    }


def build_home_page(rows: list, output_path: str, base_url: str) -> str:
    home_page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Journals</title>

    <link rel="stylesheet" href="style.css">
    <link rel="icon" href="favicon.jpg">

    <meta property="og:title" content="Journals">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{base_url}/">
    <meta property="og:description" content="H-hey... what are you doing going around posting links to my letters... d-don't do that bakahead...">
    <meta property="og:image" content="{base_url}/favicon.jpg">
    <meta content="#dfa0a9" name="theme-color" />
    <meta property="og:logo" content="{base_url}/favicon.jpg">
    <meta content="summary_large_image" name="twitter:card" />

    <script src="home.js"></script>
</head>
<body>
    <h1 class="home-title">Journals</h1>
    <div class="journal-controls">
        <input id="searchBox" type="text" placeholder="Search here..." />
        <select id="dateFormat" title="Date format">
            <option value="yyyy-mm-dd" selected>YYYY-MM-DD</option>
            <option value="dd/mm/yyyy">DD/MM/YYYY</option>
            <option value="long">Month Day Year</option>
        </select>
        <select id="sortBy" title="Sort by">
            <option value="date-desc" selected>Newest first</option>
            <option value="date-asc">Oldest first</option>
            <option value="title-asc">Title A-Z</option>
            <option value="title-desc">Title Z-A</option>
        </select>
    </div>
    <div id="journalCount" class="journal-count">
        <span id="countValue">0</span> entries
    </div>
    <div class="journal-list">
"""

    for row in rows[::-1]:
        clean_text = re.sub(r"<br\s*/?>|</?p[^>]*>", " ", row["text"])
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        home_page_html += f"""        <a href="{row["link"]}" class="journal-row">
                <div class="journal-info">
                    <div class="journal-date">{row["date"]}</div>
                    <div class="journal-text">{clean_text}</div>
                </div>
                <div class="journal-thumbnails {row["layout"]}">{row["thumbnails"]}</div>
            </a>
"""

    home_page_html += "    </div>\n</body></html>"

    home_page_path = os.path.join(os.getcwd(), output_path)
    with open(home_page_path, "w", encoding="utf-8") as f:
        f.write(home_page_html)

    return home_page_path


# Folder helpers
def pick_folder() -> str | None:
    if platform.system() == "Linux":
        try:
            result = subprocess.run(
                ["zenity", "--file-selection", "--directory"],
                stdout=subprocess.PIPE,
                text=True,
            )
            return result.stdout.strip() or None
        except FileNotFoundError:
            return None
    return filedialog.askdirectory() or None


def find_paths(folder_path: str) -> tuple[str | None, str | None]:
    entries_path = resources_path = None
    for root_dir, dirs, _ in os.walk(folder_path):
        if "Entries" in dirs and not entries_path:
            entries_path = os.path.join(root_dir, "Entries")
        if "Resources" in dirs and not resources_path:
            resources_path = os.path.join(root_dir, "Resources")
        if entries_path and resources_path:
            break
    return entries_path, resources_path


def setup_output_folders() -> tuple[str, str]:
    html_output_path = os.path.join(os.getcwd(), JOURNAL_OUTPUT_PATH)
    thumbnails_path = os.path.join(os.getcwd(), "journals", "thumbnails")
    if os.path.exists(JOURNAL_OUTPUT_PATH):
        shutil.rmtree(JOURNAL_OUTPUT_PATH)
    if os.path.exists(JOURNAL_BASE_FILE):
        os.remove(JOURNAL_BASE_FILE)
    os.makedirs(html_output_path, exist_ok=True)
    os.makedirs(thumbnails_path, exist_ok=True)
    return html_output_path, thumbnails_path


# Main
def open_journal_folder():
    start_time = time.time()
    folder_path = pick_folder()
    if not folder_path:
        return

    entries_path, resources_path = find_paths(folder_path)
    if not entries_path:
        print("Error: Entries folder not found")
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

    print(f"Processing {len(files)} journal entries...")

    results = [None] * len(files)
    completed = 0
    media_count = 0
    max_workers = max(1, os.cpu_count() or 1)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                process_entry,
                filename,
                entries_path,
                resources_path,
                html_output_path,
                thumbnails_path,
            ): idx
            for idx, filename in enumerate(files)
        }

        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            filename = files[idx]
            try:
                output = future.result(timeout=60)
            except TimeoutError:
                output = None
                print(f"\nWarning: timeout processing {filename}", file=sys.stderr)
            except Exception as e:
                output = None
                print(f"\nError processing {filename}: {e}", file=sys.stderr)

            results[idx] = (filename, output)
            if output:
                media_count += len(output[1])
            completed += 1
            filled = int(40 * completed / len(files))
            bar = "#" * filled + "-" * (40 - filled)
            pct = int(100 * completed / len(files))
            print(f"\r[{bar}] {pct}% ({completed}/{len(files)})", end="", flush=True)

    rows: list[dict] = []
    large_files_to_upload: list[tuple[str, str]] = []

    for idx, (filename, output) in enumerate(results):
        if output is not None:
            layout_class = f"layout-{idx % 5 + 1}"
            rows.append(build_home_row(filename, output, layout_class))
            if len(output) > 2:
                large_files_to_upload.extend(output[2])

    build_home_page(rows, JOURNAL_BASE_FILE, BASE_URL)

    print("\n" + "-" * 40)

    elapsed = time.time() - start_time
    avg = elapsed / media_count if media_count else 0
    print(f"\nAll entries processed.")
    print(
        f"Total time: {elapsed:.2f}s  |  Avg per photo: {avg:.4f}s  ({media_count} photos)"
    )

    print("Creating journals.zip...")
    journals_zip = os.path.join(os.getcwd(), "journals.zip")
    with zipfile.ZipFile(journals_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root_dir, dirs, zip_files in os.walk("journals"):
            for file in zip_files:
                if file != "journals.zip":
                    file_path = os.path.join(root_dir, file)
                    zf.write(file_path, file_path)
    print("journals.zip created.")

    if large_files_to_upload and USE_R2:
        print(f"Uploading {len(large_files_to_upload)} large files to R2...")
        with ThreadPoolExecutor(max_workers=8) as upload_pool:
            upload_futures = {
                upload_pool.submit(upload_to_r2, local_path, r2_key): (
                    local_path,
                    r2_key,
                )
                for local_path, r2_key in large_files_to_upload
            }
            for i, uf in enumerate(as_completed(upload_futures), 1):
                local_path, _ = upload_futures[uf]
                ok = uf.result()
                status = "✓" if ok else "✗ Failed"
                print(
                    f"  [{i}/{len(large_files_to_upload)}] {status} {os.path.basename(local_path)}"
                )
        print("R2 upload complete.")

    print("Everything completed successfully!")


def main():
    open_journal_folder()


if __name__ == "__main__":
    main()
