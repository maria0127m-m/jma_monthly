import requests
from PIL import Image
import io
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1384763822048411660/q-sgwyB8aSyu_ObaOrMWosZ68sThIWDtZCp7tE5cW1Vk_e1UYmvdYhD91tcMTj4D6blW"  # ← 差し替えてください

# JST基準で「前月」の YYMM を取得（例: 2025年6月 → '2505'）
def get_yymm():
    jst_now = datetime.utcnow() + timedelta(hours=9)
    first_day = jst_now.replace(day=1)
    last_month = first_day - timedelta(days=1)
    return last_month.strftime('%y%m'), last_month.strftime('%Y'), last_month.strftime('%m')

def get_monthly_pdf():
    url = "https://ds.data.jma.go.jp/tcc/tcc/products/model/monthly_discussion/latest.pdf"
    res = requests.get(url)
    return res.content if res.status_code == 200 else None

def get_image(url):
    res = requests.get(url)
    return Image.open(io.BytesIO(res.content)).convert("RGB") if res.status_code == 200 else None

def concat_images(img1, img2):
    w = max(img1.width, img2.width)
    h = img1.height + img2.height
    combined = Image.new("RGB", (w, h))
    combined.paste(img1, (0, 0))
    combined.paste(img2, (0, img1.height))
    out = io.BytesIO()
    combined.save(out, format="PNG")
    out.seek(0)
    return out

def post_to_discord():
    yymm, yyyy, mm = get_yymm()

    pdf_data = get_monthly_pdf()
    if not pdf_data:
        print("❌ PDF取得失敗")
        return

    urls = [
        f"https://www.data.jma.go.jp/tcc/tcc/products/climate/db/monitor/monthly/ClimMIn{yymm}e.png",
        f"https://ds.data.jma.go.jp/tcc/tcc/products/climate/db_JP/monitor/monthly/gprt{yymm}.gif",
        f"https://www.data.jma.go.jp/cpd/data/elnino/clmrep/fig/{yyyy}/{mm}/ssta-gl_color.gif",
        "https://www.data.jma.go.jp/tcc/tcc/products/elnino/gif/c_nino3.gif"
    ]

    imgs = [get_image(url) for url in urls]
    if None in imgs:
        print("❌ 画像取得に失敗")
        return

    img1 = concat_images(imgs[0], imgs[1])
    img2 = concat_images(imgs[2], imgs[3])

    files = {
        "file1": ("monthly_report.pdf", pdf_data, "application/pdf"),
        "file2": ("climate1.png", img1, "image/png"),
        "file3": ("climate2.png", img2, "image/png")
    }

    content = f"📄 気象庁 月例資料（{yyyy}年{mm}月分）+ 🌍 気候図まとめ"

    res = requests.post(DISCORD_WEBHOOK_URL, data={"content": content}, files=files)
    if res.status_code == 204:
        print("✅ 投稿成功")
    else:
        print(f"⚠ 投稿失敗: {res.status_code}, {res.text}")

if __name__ == "__main__":
    post_to_discord()
