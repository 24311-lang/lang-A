import os
import random
import requests
import urllib.parse
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
# OpenAI 대신 google-genai 라이브러리 임포트
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

app = Flask(__name__)

# Gemini 클라이언트 초기화 (기본적으로 환경변수 GEMINI_API_KEY를 참조합니다)
# .env 파일에 GEMINI_API_KEY="AIzaSy..." 형태로 저장해두세요.
client = genai.Client()

def kakao_text(text):
    """카카오톡 텍스트 응답 규격 생성 (1000자 제한 안전장치)"""
    # 만약의 상황을 대비해 950자에서 자르고 말줄임표를 추가합니다.
    safe_text = text[:950] + "..." if len(text) > 950 else text
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": safe_text
                }
            }]
        }
    }

@app.route("/", methods=["GET"])
def home():
    return "Server is running."

# 기존 테스트용
@app.route("/text", methods=["GET", "POST"])
def text_skill():
    return jsonify(kakao_text(str(random.randint(1, 10))))

@app.route("/image", methods=["GET", "POST"])
def image_skill():
    response = {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleImage": {
                    "imageUrl": "https://t1.daumcdn.net/friends/prod/category/M001_friends_ryan2.jpg",
                    "altText": "hello I'm Ryan"
                }
            }]
        }
    }
    return jsonify(response)

# 1. 데이터 그대로 주고받기
@app.route("/echo", methods=["POST"])
def echo_skill():
    data = request.get_json(silent=True) or {}
    user_input = data.get("userRequest", {}).get("utterance", "입력값이 없습니다.")
    return jsonify(kakao_text(user_input))

# 3. 시간/발화/파라미터 확인
@app.route("/params-check", methods=["POST"])
def params_check():
    data = request.get_json(silent=True) or {}
    user_request = data.get("userRequest", {})
    action = data.get("action", {})
    params = action.get("params", {})

    a = user_request.get("timezone", "timezone 없음")
    b = user_request.get("utterance", "utterance 없음")
    c = params.get("파라미터", "파라미터 없음")
    d = params.get("파라미터2", "파라미터2 없음")

    text = f"{a} / {b} / {c} / {d}"
    return jsonify(kakao_text(text))

# 4. RSS 방식을 활용한 구글 뉴스 가져오기
@app.route("/google-news", methods=["POST"])
def google_news():
    data = request.get_json(silent=True) or {}
    y = data.get("action", {}).get("params", {}).get("파라미터", "").strip()

    if not y:
        return jsonify(kakao_text("파라미터 값이 없습니다."))

    query = urllib.parse.quote(y)
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "xml")
        items = soup.find_all("item")

        titles = []
        for item in items[:5]:
            title = item.title.text
            if title:
                titles.append(title)

        if titles:
            result = f"['{y}'] 뉴스 검색 결과:\n\n" + "\n\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
        else:
            result = f"['{y}']에 대한 검색 결과를 찾지 못했습니다."

    except Exception as e:
        result = f"뉴스 조회 중 오류 발생: {str(e)}"

    return jsonify(kakao_text(result))

# 5. [수정됨] 파라미터로 Gemini 연동하기
@app.route("/gemini-param", methods=["POST"])
def gemini_param():
    data = request.get_json(silent=True) or {}
    tt = data.get("action", {}).get("params", {}).get("파라미터", "").strip()

    if not tt:
        return jsonify(kakao_text("파라미터 값이 없습니다."))

    if not os.getenv("GEMINI_API_KEY"):
        return jsonify(kakao_text("GEMINI_API_KEY 환경변수가 설정되지 않았습니다."))

    try:
        # 최신 배포 및 효율성이 뛰어난 gemini-2.5-flash 모델 사용
        # 시스템 프롬프트(페르소나)와 글자 수 제한 설정을 config로 전달합니다.
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=tt,
            config=types.GenerateContentConfig(
                system_instruction="당신은 유능한 카카오톡 챗봇입니다. 답변은 간결하고 명확하게 하세요.",
                max_output_tokens=500,
                temperature=0.7
            )
        )
        result_text = response.text.strip()
        
    except Exception as e:
        result_text = f"Gemini 호출 중 오류 발생: {str(e)}"

    return jsonify(kakao_text(result_text))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
