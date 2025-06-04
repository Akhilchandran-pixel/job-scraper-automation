import os
import requests
from bs4 import BeautifulSoup
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials
import telegram

# --- Config ---
SHEET_NAME = "JobScraper"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LI_AT_COOKIE = os.getenv("LI_AT_COOKIE")  # Add this secret in GitHub

# --- Google Sheets Auth ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# --- LinkedIn Scraper (with cookies and separate keyword searches) ---
def scrape_linkedin_jobs():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": f"li_at={LI_AT_COOKIE}"
    }

    keywords = ["Research Associate", "Analyst"]
    jobs = []

    for keyword in keywords:
        search_url = (
            "https://www.linkedin.com/jobs/search"
            f"?keywords={keyword.replace(' ', '%20')}&location=India&f_TPR=r86400"
        )
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for job_card in soup.find_all("li"):
            title = job_card.find("h3")
            if not title:
                continue
            title = title.text.strip()
            company = job_card.find("h4").text.strip() if job_card.find("h4") else "Unknown"
            location = job_card.find("span", class_="job-result-card__location")
            location = location.text.strip() if location else "Unknown"
            job_url = job_card.find("a")["href"]

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "url": job_url
            })

    return jobs

# --- Push to Google Sheet ---
def push_to_google_sheet(jobs):
    existing_urls = sheet.col_values(4)
    for job in jobs:
        if job["url"] not in existing_urls:
            sheet.append_row([job["title"], job["company"], job["location"], job["url"]])

# --- Send Telegram Alerts ---
def send_telegram_alerts(jobs):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    for job in jobs:
        msg = f"📌 *{job['title']}*\n🏢 {job['company']}\n📍 {job['location']}\n🔗 {job['url']}"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")

# --- Main ---
if __name__ == "__main__":
    jobs = scrape_linkedin_jobs()
    if jobs:
        push_to_google_sheet(jobs)
        send_telegram_alerts(jobs)
    else:
        print("No jobs found.")
