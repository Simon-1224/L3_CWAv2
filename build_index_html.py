#!/usr/bin/env python3
"""Build index.html for Stlite (WebAssembly Streamlit) deployment on Vercel."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

FILES_TO_EMBED = [
    "app.py",
    "config.py",
    "data_processor.py",
    "database.py",
    "map_utils.py",
    "weather_api.py",
    "sqlite3.py",
]

REQUIREMENTS = [
    "requests",
    "pandas",
    "plotly",
    "folium",
    "streamlit-folium",
    "python-dotenv",
    "pyodide-http",
]


def generate_index_html() -> str:
    files_dict = {}
    for filename in FILES_TO_EMBED:
        filepath = BASE_DIR / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            files_dict[filename] = content
        else:
            print(f"Warning: File not found: {filename}")

    # Safely serialize files dictionary to JSON for embedding in <script>
    files_json = json.dumps(files_dict, ensure_ascii=False)
    # Prevent closing script tag issues
    files_json = files_json.replace("</script", "<\\/script")

    requirements_json = json.dumps(REQUIREMENTS, indent=8)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1, shrink-to-fit=no"
    />
    <title>Taiwan Weather Forecast Dashboard | 台灣天氣預報儀表板</title>
    <!-- Stlite Mountable CSS -->
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/@stlite/mountable@0.75.0/build/stlite.css"
    />
    <style>
      html,
      body {{
        margin: 0;
        padding: 0;
        height: 100%;
        overflow: hidden;
        background-color: #0e1117;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      }}
      #root {{
        height: 100vh;
        width: 100vw;
      }}
    </style>
  </head>
  <body>
    <div id="root"></div>

    <!-- Stlite Mountable JS -->
    <script src="https://cdn.jsdelivr.net/npm/@stlite/mountable@0.75.0/build/stlite.js"></script>
    <script>
      const embeddedFiles = {files_json};

      stlite.mount(
        {{
          entrypoint: "app.py",
          files: embeddedFiles,
          requirements: {requirements_json},
        }},
        document.getElementById("root")
      );
    </script>
  </body>
</html>
"""
    return html


def main():
    html_content = generate_index_html()
    output_path = BASE_DIR / "index.html"
    output_path.write_text(html_content, encoding="utf-8")
    print(f"Successfully generated {output_path} ({len(html_content):,} bytes)")


if __name__ == "__main__":
    main()
