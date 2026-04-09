# Auto Manual Review Tool

A utility for streamlining the manual review process for flagged users on kog.tw. It automates data scraping, cookie management, status checks, and Discord message generation. Available as both a Jupyter Notebook (interactive) and a standalone Python script.

---

## Environment Setup

### IDE
- **[Visual Studio Code](https://code.visualstudio.com/)** recommended
  - Install the **Jupyter** extension (by Microsoft) for notebook support: `Ctrl+Shift+X` → search `Jupyter`

### Python
- Python **3.9+** required
- Use `venv`, `conda`, or your preferred environment manager

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/vidathegoat/auto-review.git
cd auto-review
```

### 2. Install Dependencies

```bash
pip install undetected-chromedriver curl_cffi beautifulsoup4 pandas pyperclip ipywidgets ipyaggrid
```

| Package | Purpose |
|---|---|
| `undetected-chromedriver` | Browser automation for login (bypasses bot detection) |
| `curl_cffi` | HTTP requests with browser impersonation |
| `beautifulsoup4` | HTML parsing |
| `pandas` | Table display in notebook |
| `pyperclip` | Copy generated message to clipboard |
| `ipywidgets` / `ipyaggrid` | Interactive UI elements in notebook |

> Google Chrome must be installed. `undetected-chromedriver` manages the matching ChromeDriver version automatically.

Alternatively, run **Cell 4** in the notebook to install everything automatically.

### 3. Run

**Notebook (interactive):**
```bash
jupyter notebook auto-review.ipynb
```

**Script (CLI):**
```bash
python auto-review.py
```

---

## Project Structure

```
.
├── auto-review.ipynb      # Interactive notebook version
├── auto-review.py         # Standalone CLI script
├── cookies.json           # Saved session cookies (git-ignored)
├── debug_output/          # Debug HTML snapshots (git-ignored)
├── .gitignore
├── LICENSE
└── README.md
```

---

## Features

- Scrapes player migration data by reference number
- Checks account registration and migration/ban status
- Matches player IPs against usernames via internal API
- Generates formatted Discord messages for moderators
- Caches session cookies to skip login on subsequent runs
- Saves raw HTML snapshots to `debug_output/` for troubleshooting

---

## Tips

- If the site layout changes, re-check the BeautifulSoup selectors in the scraping functions.
- If your Chrome version updates and the driver breaks, reinstalling `undetected-chromedriver` usually fixes it.
- In the notebook, individual cells can be re-run without restarting unless an error interrupts execution.

---

## License

MIT License © 2025 Vida

See the [LICENSE](./LICENSE) file for details.
