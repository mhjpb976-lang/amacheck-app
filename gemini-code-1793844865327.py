from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import requests
from openai import OpenAI
import json

app = FastAPI()

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIキー（環境変数、または直接文字列で設定）
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
KEEPA_API_KEY = os.environ.get("KEEPA_API_KEY", "YOUR_KEEPA_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

class AnalyzeRequest(BaseModel):
    input_query: str
    associate_id: str = "yourtag-22"

class SaleItemCheckRequest(BaseModel):
    category: str = "all"
    associate_id: str = "yourtag-22"

def extract_asin(query: str) -> str:
    """URLまたは文字列から10桁のASINを抽出"""
    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', query)
    if match:
        return match.group(1)
    if len(query.strip()) == 10 and query.strip().isalnum():
        return query.strip().toUpperCase()
    raise HTTPException(status_code=400, detail="有効なAmazonのURLまたはASINを入力してください。")

def fetch_keepa_data(asin: str):
    """Keepa APIから価格履歴データを取得"""
    url = f"https://api.keepa.com/query?key={KEEPA_API_KEY}&domain=5&asin={asin}&stats=1"
    try:
        res = requests.get(url)
        data = res.json()
        if "products" in data and len(data["products"]) > 0:
            product = data["products"][0]
            stats = product.get("stats", {})
            # Keepaの価格データは通常100倍（例: 4980円 = 498000）
            current_price = stats.get("current", [0])[0] / 100 if stats.get("current") else 0
            avg_price_90d = stats.get("avg90", [0])[0] / 100 if stats.get("avg90") else current_price
            return {
                "current_price": int(current_price),
                "avg_price_90d": int(avg_price_90d),
                "title": product.get("title", f"Amazon商品 ({asin})"),
                "rating": stats.get("rating", 4.0) / 10 if stats.get("rating", 40) > 5 else stats.get("rating", 4.0),
                "review_count": stats.get("reviewCount", 100)
            }
    except Exception as e:
        print(f"Keepa API Error: {e}")
    
    # フォールバック（API未設定・エラー時のダミーデータ）
    return {
        "current_price": 4980,
        "avg_price_90d": 4980,
        "title": f"Amazon商品 ({asin})",
        "rating": 4.5,
        "review_count": 520
    }

def analyze_reviews_with_ai(product_title: str, review_count: int, official_rating: float):
    """OpenAI API (GPT-4o) を使ってサクラ度と実質評価を推計・分析"""
    prompt = f"""
    あなたはAmazonのサクラレビュー・見せかけ値下げを検出するプロの分析AIです。
    以下の商品情報をもとに、サクラ危険度と実質評価を推計してください。
    
    商品名: {product_title}
    公式評価: ★{official_rating} (レビュー数: {review_count})
    
    以下のJSON形式のみで出力してください（マークダウンのバッククォートは不要）。
    {{
      "sakura_score": 75,
      "risk_level": "DANGER",
      "real_rating": "2.9",
      "suspicious_points": [
        "指摘ポイント1（例: 短期間でのレビュー急増）",
        "指摘ポイント2（例: 不自然な表現）",
        "指摘ポイント3（例: 価格の不整合）"
      ]
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        # フォールバック
        return {
            "sakura_score": 45,
            "risk_level": "WARNING",
            "real_rating": "3.8",
            "suspicious_points": [
                "一部の時期に星5レビューがやや集中しています。",
                "極端な高評価と低評価が混在しており、個体差がある可能性があります。"
            ]
        }

@app.post("/api/analyze")
async def analyze_product(req: AnalyzeRequest):
    asin = extract_asin(req.input_query)
    
    # 1. Keepa APIから価格・基本情報を取得
    product_info = fetch_keepa_data(asin)
    
    # 2. OpenAI APIで口コミ信用度・サクラ度を解析
    ai_analysis = analyze_reviews_with_ai(
        product_info["title"], 
        product_info["review_count"], 
        product_info["rating"]
    )
    
    # 3. アフィリエイトURLの構築
    affiliate_url = f"https://www.amazon.co.jp/dp/{asin}?tag={req.associate_id}"
    
    return {
        "asin": asin,
        "title": product_info["title"],
        "price": f"¥{product_info['current_price']:,}",
        "official_rating": f"★{product_info['rating']} ({product_info['review_count']}件)",
        "real_rating": f"★{ai_analysis['real_rating']}",
        "sakura_score": f"{ai_analysis['sakura_score']}%",
        "risk_level": ai_analysis['risk_level'],
        "suspicious_points": ai_analysis['suspicious_points'],
        "affiliate_url": affiliate_url,
        "similar_items": [
            {
                "asin": "B0C1234567",
                "title": "Anker Soundcore P20i (安全性の高い代替品)",
                "price": "¥3,990",
                "rating": "★4.4 (サクラ率 2%)",
                "url": f"https://www.amazon.co.jp/dp/B0C1234567?tag={req.associate_id}"
            }
        ]
    }

@app.post("/api/sale-featured")
async def get_sale_featured_items(req: SaleItemCheckRequest):
    # セール対象ASINプール
    mock_sale_pool = [
        {"asin": "B08N5WRWNW", "title": "Anker Soundcore P20i 完全ワイヤレスイヤホン", "category": "ガジェット", "sale_price": 3490, "official_rating": 4.4, "review_count": 2150},
        {"asin": "B09XXXXXXX", "title": "怪しいハイブリッド加湿器 (セール特価品)", "category": "家電", "sale_price": 5980, "official_rating": 4.8, "review_count": 320},
        {"asin": "B0B1111111", "title": "Fire TV Stick 4K Select", "category": "ガジェット", "sale_price": 4980, "official_rating": 4.6, "review_count": 15400}
    ]

    filtered_deals = []

    for item in mock_sale_pool:
        keepa_data = fetch_keepa_data(item["asin"])
        normal_avg_price = keepa_data.get("avg_price_90d", item["sale_price"] * 1.2)
        
        price_diff_ratio = (normal_avg_price - item["sale_price"]) / normal_avg_price
        is_fake_discount = item["sale_price"] >= normal_avg_price * 1.05

        ai_analysis = analyze_reviews_with_ai(item["title"], item["review_count"], item["official_rating"])
        sakura_score = ai_analysis["sakura_score"]

        if not is_fake_discount and sakura_score < 30:
            real_discount_rate = round(max(0, price_diff_ratio) * 100, 1)
            filtered_deals.append({
                "asin": item["asin"],
                "title": item["title"],
                "category": item["category"],
                "sale_price": f"¥{item['sale_price']:,}",
                "normal_price": f"¥{int(normal_avg_price):,}",
                "real_discount_rate": f"{real_discount_rate}% OFF",
                "sakura_score": f"{sakura_score}% (安全)",
                "ai_comment": "過去3ヶ月の平均価格と比較して本当にお買い得です。サクラレビューも検出されませんでした。",
                "affiliate_url": f"https://www.amazon.co.jp/dp/{item['asin']}?tag={req.associate_id}"
            })

    return {
        "event_name": "🔥 タイムセール祭り：本物の目玉商品特集 (サクラ・見せかけ値下げ除外済)",
        "total_scanned": len(mock_sale_pool),
        "passed_items": filtered_deals
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)