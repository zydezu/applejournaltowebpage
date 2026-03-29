import os
import platform
import re
import shutil
import subprocess
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()


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


def open_journal_folder():
    folder_path = pick_folder()
    if not folder_path:
        return

    entries_path = None
    for root, dirs, files in os.walk(folder_path):
        if "Entries" in dirs:
            entries_path = os.path.join(root, "Entries")
            break

    if not entries_path:
        print("Error: entries folder not found")
        return

    output_path = os.path.join(os.getcwd(), "journals/md")
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)

    files = sorted(
        f
        for f in os.listdir(entries_path)
        if os.path.isfile(os.path.join(entries_path, f))
    )

    for filename in files:
        file_path = os.path.join(entries_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            title = extract_title(content)
            media_links = extract_media_links(content)

            entry_folder_name = filename.replace(".html", "")
            entry_folder = os.path.join(output_path, entry_folder_name)
            os.makedirs(entry_folder, exist_ok=True)

            md_path = os.path.join(entry_folder, "content.md")

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                for link in media_links:
                    f.write(f"{link}\n")

            print(f"Created: {entry_folder_name}/content.md")


def extract_title(html_content):
    match = re.search(r"<div class='title'>([^<]+)</div>", html_content)
    return match.group(1) if match else ""


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
