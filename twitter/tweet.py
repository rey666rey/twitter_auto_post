import random
import requests
import re

def query_lm_studio(prompt: str, model_url: str = "http://localhost:1234/v1/chat/completions", model_name: str = "local-model") -> str:
    """
    Отправляет prompt к локальной модели через LM Studio и возвращает очищенный финальный ответ.
    Если ответ содержит китайские символы — возвращает смайлик 💋.
    Удаляет лишние символы вроде \r (перенос каретки).
    """
    headers = {
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(model_url, headers=headers, json=payload)

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    try:
        raw = response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return "Error: unexpected response format"

    # 🧹 Очистка <think>...</think> и <think)...> строк
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    cleaned = re.sub(r"<think\).*?(\n|$)", "", cleaned, flags=re.DOTALL)

    # 🧹 Удаление символа \r и других управляющих символов, кроме \n
    cleaned = re.sub(r"[\r\x00-\x08\x0b-\x1f\x7f]", "", cleaned)

    # 🔍 Проверка на китайские символы
    chinese_pattern = re.compile(r"[\u4e00-\u9fff]")
    if chinese_pattern.search(cleaned):
        return "💋"

    # 🧠 Вернуть последнюю непустую строку
    lines = [line.strip() for line in cleaned.strip().splitlines() if line.strip()]
    if lines:
        return lines[-1]

    return cleaned  # fallback

def choose_one_string_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip()]
    return random.choice(lines) if lines else ''