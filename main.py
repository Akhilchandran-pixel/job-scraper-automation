import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import telegram

# --- Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SHEET_NAME = "JobScraper"  # Name of your Google Sheet tab

# --- Setup Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # Use the first sheet

# --- Setup Telegram Bot ---
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# --- LinkedIn Scraper ---
def scrape_linkedin():
    base_url = "https://www.linkedin.com/jobs/search"
    params = {
        "keywords": "Research Associate OR Analyst",
        "location": "India",
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "f_TPR": "r86400",  # Posted in past 24 hours
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(base_url, headers=headers, params=params)

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    for li in soup.find_all("li", class_="result-card"):
        try:
            title = li.find("h3").text.strip()
            company = li.find("h4").text.strip()
            location = li.find("span", class_="job-result-card__location").text.strip()
            job_link = li.find("a", class_="result-card__full-card-link")["href"]
            easy_apply = "Easy Apply" in li.text
            jobs.append([datetime.now().isoformat(), title, company, location, job_link, "Yes" if easy_apply else "No"])
        except:
            continue
    return jobs

# --- Main Flow ---
def main():
    jobs = scrape_linkedin()
    if not jobs:
        print("No jobs found.")
        return

    # Header row (only if empty)
    if not sheet.get_all_values():
        sheet.append_row(["Date", "Title", "Company", "Location", "Link", "Easy Apply"])

    for job in jobs:
        sheet.append_row(job)

    # Telegram summary
    message = f"📌 Found {len(jobs)} new jobs:\n\n"
    for job in jobs[:5]:  # Limit to top 5 in message
        message += f"🧾 {job[1]} at {job[2]} ({job[3]})\n🔗 {job[4]}\n\n"
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

if __name__ == "__main__":
    main()
