import requests
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1384763822048411660/q-sgwyB8aSyu_ObaOrMWosZ68sThIWDtZCp7tE5cW1Vk_e1UYmvdYhD91tcMTj4D6blW"  

# 前月の年月を取得（yymm形式・yyyy・mm）
def get_yymm():
    jst_now = datetime.utcnow() + timedelta(hours=9)
    first_day = jst_now.replace(day=1)
    last_month = first_day - timedelta(days=1)
    return last_month.strftime('%y%m'), last_month.strftime('%Y'), last_month.strftime('%m')

# PDF取得
def get_monthly_pdf():
    url = "https://ds.data.jma.go.jp/tcc/tcc/products/model/monthly_discussion/latest.pdf"
    res = requests.get(url)
    return res.content if res.status_code == 200 else None

# 画像取得
def get_image(url):
    res = requests.get(url)
    return Image.open(io.BytesIO(res.content)).convert("RGB") if res.status_code == 200 else None

# 余白 + タイトルラベル追加
def add_margin_and_label(image, label, margin=30, color=(255, 255, 255)):
    new_width = image.width + margin * 2
    new_height = image.height + margin * 2
    new_img = Image.new("RGB", (new_width, new_height), color)
    new_img.paste(image, (margin, margin))

    # ラベル描画
    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        font = ImageFont.load_default()

    draw.text((margin + 30, margin - 5), label, fill="black", font=font, stroke_width=2, stroke_fill="white")
    return new_img

# 2枚縦結合（幅を揃える）
def concat_images_two_uniform(img1, img2):
    max_width = max(img1.width, img2.width)

    def resize(img):
        if img.width == max_width:
            return img
        new_height = int(img.height * (max_width / img.width))
        return img.resize((max_width, new_height), Image.BICUBIC)

    img1 = resize(img1)
    img2 = resize(img2)

    combined = Image.new("RGB", (max_width, img1.height + img2.height))
    combined.paste(img1, (0, 0))
    combined.paste(img2, (0, img1.height))

    out = io.BytesIO()
    combined.save(out, format="PNG")
    out.seek(0)
    return out

# 3枚縦結合（幅を揃える）
def concat_images_three(img1, img2, img3):
    max_width = max(img.width for img in [img1, img2, img3])

    def resize(img):
        if img.width == max_width:
            return img
        new_height = int(img.height * (max_width / img.width))
        return img.resize((max_width, new_height), Image.BICUBIC)

    imgs = [resize(i) for i in [img1, img2, img3]]
    total_height = sum(i.height for i in imgs)

    combined = Image.new("RGB", (max_width, total_height))
    y = 0
    for img in imgs:
        combined.paste(img, (0, y))
        y += img.height

    out = io.BytesIO()
    combined.save(out, format="PNG")
    out.seek(0)
    return out

# 投稿処理
def post_to_discord():
    yymm, yyyy, mm = get_yymm()

    # PDF取得
    pdf_data = get_monthly_pdf()
    if not pdf_data:
        print("❌ PDF取得失敗")
        return

    # 画像URLとラベル（図順に合わせて）
    urls = [
        f"https://www.data.jma.go.jp/tcc/tcc/products/climate/db/monitor/monthly/ClimMIn{yymm}e.png",
        f"https://ds.data.jma.go.jp/tcc/tcc/products/climate/db_JP/monitor/monthly/gprt{yymm}.gif",
        f"https://www.data.jma.go.jp/cpd/data/elnino/clmrep/fig/{yyyy}/{mm}/ssta-gl_color.gif",
        "https://www.data.jma.go.jp/tcc/tcc/products/elnino/gif/c_nino3.gif",
        "https://www.data.jma.go.jp/tcc/tcc/products/elnino/gif/c_iowpac.gif"
    ]

    labels = [
        "Extreme Climate Events",
        "Monthly Precipitation Ratio",
        "Monthly Mean SST Anomaly",
        "NINO.3 & SOI",
        "NINO.WEST & IOBW"
    ]

    # 画像取得＋ラベル・余白追加
    imgs = []
    for url, label in zip(urls, labels):
        img = get_image(url)
        if img:
            img = add_margin_and_label(img, label, margin=30)
        imgs.append(img)

    if None in imgs:
        print("❌ 画像取得に失敗")
        return

    # 縦結合
    img1 = concat_images_two_uniform(imgs[0], imgs[1])
    img2 = concat_images_three(imgs[2], imgs[3], imgs[4])

    files = {
        "file1": ("monthly_report.pdf", pdf_data, "application/pdf"),
        "file2": ("climate_summary1.png", img1, "image/png"),
        "file3": ("climate_summary2.png", img2, "image/png")
    }

    content = f"📄 気象庁 月例資料（{yyyy}年{mm}月分）\n🌍 気候図を画像でまとめて投稿します。"

    res = requests.post(DISCORD_WEBHOOK_URL, data={"content": content}, files=files)
    if res.status_code == 204:
        print("✅ 投稿成功")
    else:
        print(f"⚠ 投稿失敗: {res.status_code}, {res.text}")

if __name__ == "__main__":
    post_to_discord()
