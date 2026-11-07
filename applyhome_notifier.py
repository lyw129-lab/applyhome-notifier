import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

APPLYHOME_URL = "https://www.applyhome.co.kr/ai/aio/selectAioLttotPblancList.do"
RESTRICTED_DISTRICTS = ["강남구", "서초구", "송파구", "용산구"]

def fetch_eligible_announcements():
    target_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(APPLYHOME_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select(".tbl_st tbody tr")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                house_name = cols[0].get_text(strip=True)
                location = cols[1].get_text(strip=True)
                ann_date = cols[2].get_text(strip=True)
                
                link_tag = cols[0].find("a")
                detail_link = f"https://www.applyhome.co.kr{link_tag['href']}" if link_tag and 'href' in link_tag.attrs else "https://www.applyhome.co.kr"
                map_link = f"https://map.naver.com/v5/search/{quote(house_name)}"

                if "서울" not in location:
                    continue

                if any(district in location or district in house_name for district in RESTRICTED_DISTRICTS):
                    continue

                target_list.append({
                    "name": house_name,
                    "location": location,
                    "date": ann_date,
                    "link": detail_link,
                    "map_link": map_link
                })
    except Exception as e:
        print(f"공고 수집 중 오류: {e}")

    return target_list

def send_email_notification(targets):
    if not targets:
        print("신규 지원 대상 공고가 없습니다.")
        return

    subject = f"[청약 알림] 서울 비규제 추첨제 신규 공고 ({len(targets)}건)"

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; color: #333; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }}
            .header {{ background-color: #1e3a8a; color: #ffffff; padding: 20px; font-size: 18px; font-weight: bold; }}
            .sub-header {{ font-size: 13px; color: #93c5fd; margin-top: 5px; font-weight: normal; }}
            .content {{ padding: 20px; background-color: #ffffff; }}
            .card {{ border: 1px solid #edf2f7; border-left: 4px solid #2563eb; border-radius: 6px; padding: 15px; margin-bottom: 15px; background-color: #f8fafc; }}
            .title {{ font-size: 16px; font-weight: bold; color: #0f172a; margin-bottom: 6px; }}
            .info {{ font-size: 14px; color: #475569; margin-bottom: 12px; }}
            .btn-group {{ display: flex; gap: 8px; }}
            .btn {{ display: inline-block; padding: 8px 14px; color: #ffffff !important; text-decoration: none; border-radius: 5px; font-size: 13px; font-weight: bold; }}
            .btn-apply {{ background-color: #2563eb; }}
            .btn-map {{ background-color: #059669; }}
            .footer {{ background-color: #f1f5f9; padding: 12px; text-align: center; font-size: 12px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                🎯 맞춤 청약 공고 알림 (오전 10시 정시 발송)
                <div class="sub-header">서울 2년 이상 거주 | 세대원 1순위 | 예치금 1,500만 원 (전 평형 추첨)</div>
            </div>
            <div class="content">
                <p>조건에 부합하는 서울 비규제지역 청약 공고가 수집되었습니다. 지도 위치와 신청 링크를 확인하세요.</p>
    """

    for item in targets:
        html_content += f"""
                <div class="card">
                    <div class="title">{item['name']}</div>
                    <div class="info">📍 위치: {item['location']}<br>📅 모집공고일: {item['date']}</div>
                    <div class="btn-group">
                        <a href="{item['link']}" class="btn btn-apply" target="_blank">청약홈 바로가기 🔗</a>
                        <a href="{item['map_link']}" class="btn btn-map" target="_blank">🗺️ 네이버 지도 보기</a>
                    </div>
                </div>
        """

    html_content += """
            </div>
            <div class="footer">GitHub Actions 파이프라인에 의해 자동 생성된 이메일입니다.</div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("이메일 발송 성공")
    except Exception as e:
        print(f"발송 실패: {e}")

if __name__ == "__main__":
    targets = fetch_eligible_announcements()
    send_email_notification(targets)
