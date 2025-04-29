# 🛠️ Auto Manual Review Tool

A Jupyter Notebook utility that streamlines the manual review process for flagged users on kog.tw. It automates data scraping, cookie management, status checks, and copy/paste message generation — all in one interactive and beginner-friendly workflow.

---

## 🚀 Getting Started

These instructions will help you get a local copy of the project up and running.

### 1. 📥 Clone the Repository

Run this in your terminal:

    git clone https://github.com/your-username/auto-manual-review.git
    cd auto-manual-review

### 2. 📦 Install Dependencies

If you're using the Jupyter Notebook (`.ipynb`), run **Cell 0** to install everything automatically:

    !pip install selenium bs4 pandas requests pyclip

Or install manually with the provided `requirements.txt`:

    pip install -r requirements.txt

> 💡 Make sure you have Google Chrome and a matching version of ChromeDriver installed:
> https://www.google.com/chrome/
> https://chromedriver.chromium.org/downloads

### 3. ▶️ Run the Notebook

Launch the notebook interface with:

    jupyter notebook AutoManualReview.ipynb

No IDE required!

---

## 📁 Project Structure

    .
    ├── auto-review.ipynb          # Main notebook script
    ├── cookies.json               # Saved cookies (excluded by .gitignore)
    ├── .gitignore                 # Git ignore config
    └── README.md                  # You are here!

---

## ⚙️ Features

✅ Scrapes player migration data by reference number  
✅ Checks account registration status  
✅ Generates formatted messages for Discord moderators  
✅ Matches player IPs against usernames using a hidden API  
✅ Displays results in clean, interactive tables  
✅ Caches session cookies to skip login for future runs  

---

## 🧠 Tips

- If the site changes, re-check selectors in BeautifulSoup.
- If ChromeDriver breaks, re-download the version that matches your browser.
- You can re-run any cell without restarting the notebook unless an error interrupts execution.

---

## 🧾 License

MIT License © 2025 Vida

---

## 🙏 Acknowledgments

- [kog.tw](https://kog.tw) for providing the platform
- [Selenium](https://www.selenium.dev/) for browser automation
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- [pandas](https://pandas.pydata.org/) for table display
- [Jupyter](https://jupyter.org/) for making it all easy to interact with
