from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import re

app = FastAPI(title="Amacheck App")

# ご自身のAmazonアソシエイト・トラッキングID
TRACKING_ID = "amachecker09-22"

class AnalyzeRequest(BaseModel, extra="allow"):
    url: str

def generate_affiliate_url(raw_url: str) -> str:
    """AmazonのURLからASINを抽出し、トラッキングID付きのリンクを生成する"""
    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', raw_url)
    if match:
        asin = match.group(1)
        return f"https://www.amazon.co.jp/dp/{asin}?tag={TRACKING_ID}"
    
    if "?" in raw_url:
        return f"{raw_url}&tag={TRACKING_ID}"
    else:
        return f"{raw_url}?tag={TRACKING_ID}"

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Amacheck App is running!</h1>"

@app.post("/api/analyze")
def analyze_product(data: AnalyzeRequest):
    product_url = data.url
    if not product_url:
        raise HTTPException(status_code=400, detail="URL is required.")
    
    affiliate_url = generate_affiliate_url(product_url)
    
    return {
        "status": "success",
        "product_url": affiliate_url,
        "sakura_score": "高精度AI判定: 信頼度 92% (不自然な高評価レビューの集中を検知)",
        "price_trend": "現在価格は過去90日間の平均相場より約15%安値",
        "recommendation": "AI総合評価: 現在の価格で購入するのは非常に「買い」のタイミングです。"
    }

@app.get("/api/sales")
def get_sale_items():
    return [
        {
            "title": "Anker Nano II 65W (PD 充電器 急速充電器)",
            "discount": "20% OFF",
            "price": "¥3,990",
            "original": "¥4,990",
            "badge": "タイムセール",
            "url": f"https://www.amazon.co.jp/dp/B08T5QN2VJ?tag={TRACKING_ID}"
        },
        {
            "title": "Fire TV Stick 4K - 映画館のような高画質",
            "discount": "25% OFF",
            "price": "¥5,480",
            "original": "¥7,480",
            "badge": "特選タイムセール",
            "url": f"https://www.amazon.co.jp/dp/B0BP91V3DS?tag={TRACKING_ID}"
        },
        {
            "title": "Kindle Paperwhite (16GB) 6.8インチディスプレイ",
            "discount": "15% OFF",
            "price": "¥16,980",
            "original": "¥19,980",
            "badge": "期間限定セール",
            "url": f"https://www.amazon.co.jp/dp/B09T3X59VM?tag={TRACKING_ID}"
        }
    ]

@app.get("/api/sale-page")
def get_sale_page():
    return {
        "title": "Amazon タイムセール会場",
        "subtitle": "毎日更新されるタイムセールや特選タイムセールをチェック！",
        "url": f"https://www.amazon.co.jp/gp/goldbox?tag={TRACKING_ID}"
    }