from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="Amacheck App")

class AnalyzeRequest(BaseModel, extra="allow"):
    url: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Amacheck App is running! Please ensure index.html is uploaded.</h1>"

@app.post("/api/analyze")
def analyze_product(data: AnalyzeRequest):
    product_url = data.url
    if not product_url:
        raise HTTPException(status_code=400, detail="URL is required.")
    
    # サンプル分析ロジック（Keepa / OpenAI連携の土台となる部分）
    return {
        "status": "success",
        "message": "Analysis completed successfully.",
        "product_url": product_url,
        "sakura_score": "低 (信頼度: 85%)",
        "price_trend": "過去3ヶ月で最安値圏",
        "recommendation": "現在の価格で購入するのはお買い得です。"
    }