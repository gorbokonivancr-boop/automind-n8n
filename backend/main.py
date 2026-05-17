import os
import random
import time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

app = FastAPI(title="AutoMind Demo API")

# Mount demos as static files
app.mount("/demos", StaticFiles(directory="demos"), name="demos")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class ReviewRequest(BaseModel):
    text: str
    rating: int

@app.post("/api/reputation/analyze")
async def analyze_review(req: ReviewRequest):
    if not OPENROUTER_API_KEY:
        # Fallback for demo if no key provided
        return {
            "sentiment": "Positive" if req.rating >= 4 else "Negative",
            "response": f"Спасибо за ваш отзыв! (Демо-ответ без API)",
            "is_demo": True
        }

    prompt = f"Клиент оставил отзыв ({req.rating} звезд): \"{req.text}\". Напиши вежливый ответ от лица администрации салона 'Эстетика'. Определи тональность (Позитивная, Нейтральная, Негативная)."

    try:
        res = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=15
        )
        data = res.json()
        ai_text = data['choices'][0]['message']['content']
        sentiment = "Позитивная" if "озитив" in ai_text else ("Негативная" if "егатив" in ai_text else "Нейтральная")
        return {"sentiment": sentiment, "response": ai_text, "is_demo": False}
    except Exception as e:
        return {"sentiment": "Unknown", "response": str(e), "error": True}

@app.post("/api/calls/summarize")
async def summarize_call(file: UploadFile = File(...)):
    # В реальном приложении здесь вызывается Whisper API (OpenAI)
    # Для демо мы имитируем задержку распознавания, но пропускаем текст через реальный GPT
    time.sleep(2)

    if not OPENROUTER_API_KEY:
        return {
            "client_name": "Анна (Демо)",
            "purpose": "Сложное окрашивание",
            "status": "Запись не состоялась",
            "conflict": "Нет мест на субботу. (Без API)",
            "score": 4,
            "transcript_fragment": "Администратор: К сожалению, мест нет."
        }

    # Имитируем, что Whisper выдал текст, и просим GPT его проанализировать
    prompt = """
    Проанализируй транскрипт звонка в салон красоты:
    'Адм: Алло, салон Эстетика.
    Кл: Здравствуйте, хочу на субботу на окрашивание.
    Адм: В субботу все занято, извините.
    Кл: Очень жаль, до свидания.'

    Выдай ответ в формате JSON:
    {"client_name": "...", "purpose": "...", "status": "...", "conflict": "...", "score": 1-5, "transcript_fragment": "..."}
    """

    try:
        res = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": { "type": "json_object" }
            },
            timeout=20
        )
        return res.json()['choices'][0]['message']['content']
    except:
        return {"error": "AI analysis failed"}

@app.get("/")
async def root():
    return {"message": "AutoMind Demo Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
