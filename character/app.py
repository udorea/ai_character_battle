from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests 
from google.api_core import exceptions
from apscheduler.schedulers.background import BackgroundScheduler 
import random 
import atexit 

load_dotenv()

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
CORS(app)

API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("오류: .env 파일에 GOOGLE_API_KEY가 설정되지 않았습니다.")

genai.configure(api_key=API_KEY)

try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Gemini 'gemini-1.5-flash-latest' 모델이 성공적으로 초기화되었습니다.")
except Exception as e:
    raise RuntimeError(f"Gemini 모델 초기화 실패: {e}. API 키와 인터넷 연결을 확인하세요.")

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

PHP_API_BASE_URL = "http://localhost/CHARACTER/backend"

FORBIDDEN_WORDS = ["금칙어 적는 곳 입니다"]

def check_profanity(text, forbidden_words):
    found_words = []
    text_lower = text.lower()
    for word in forbidden_words:
        if word.lower() in text_lower:
            found_words.append(word)
    return found_words

def get_ai_battle_response(character1_name, character1_desc, character2_name, character2_desc):
    try:
        prompt_text = f"""
        당신은 두 캐릭터 간의 가상 배틀을 시뮬레이션하고 결과를 예측하는 AI입니다.
        두 캐릭터의 정보를 바탕으로 승패를 결정하고, 그 이유를 상세히 설명해주세요.
        응답은 반드시 아래 지정된 형식(키-값 쌍)으로 작성해야 합니다.
        추가 설명이나 인사말 없이 순수하게 키-값 쌍만 출력하세요.

        ---
        캐릭터 1 이름: {character1_name}
        캐릭터 1 소개: {character1_desc}

        캐릭터 2 이름: {character2_name}
        캐릭터 2 소개: {character2_desc}
        ---

        출력 형식:
        승자: [승자 캐릭터 이름]
        패자: [패자 캐릭터 이름]
        판단_근거: [승패에 대한 상세한 이유]
        """

        response = model.generate_content(prompt_text, safety_settings=SAFETY_SETTINGS)
        ai_output = response.text
        
        print(f"\n--- Gemini Battle Raw Output ({character1_name} vs {character2_name}) ---")
        print(ai_output)
        print("----------------------------------------\n")

        parsed_data = {}
        lines = ai_output.split('\n')
        required_keys = ['승자', '패자', '판단_근거']
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            if ':' in line:
                try:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    parsed_data[key] = value
                except ValueError:
                    print(f"파싱 경고: {line_num}번째 줄 '{line}'에서 키/값 분리 실패. 형식 오류 가능성.")
            else:
                print(f"파싱 경고: {line_num}번째 줄 '{line}'에 ':'이 없습니다. 예상치 못한 응답 형식.")

        for r_key in required_keys:
            if r_key not in parsed_data or not parsed_data[r_key]:
                print(f"오류: 필수 키 '{r_key}'가 Gemini 응답에서 누락되었거나 비어 있습니다.")
                print(f"현재 파싱된 데이터: {parsed_data}")
                return {"error": "AI 배틀 결과 파싱 실패: 예상된 모든 정보를 얻지 못했습니다. Flask 콘솔의 'Gemini Battle Raw Output'을 확인하세요."}
        
        return {
            "winner": parsed_data.get('승자'),
            "loser": parsed_data.get('패자'),
            "reason": parsed_data.get('판단_근거')
        }

    except genai.types.BlockedPromptException as e:
        print(f"Gemini API 오류: 부적절한 내용으로 인해 배틀 프롬프트가 차단되었습니다. - {e.response.prompt_feedback.block_reason}")
        return {"error": "불쾌하거나 부적절한 내용이 포함되어 배틀 분석이 차단되었습니다. 다른 캐릭터를 시도해보세요."}
    except exceptions.GoogleAPIError as e:
        print(f"Gemini API 호출 중 오류 발생 (GoogleAPIError): {e}")
        return {"error": f"Gemini AI 서비스와 통신 중 오류가 발생했습니다: {e}"}
    except Exception as e:
        print(f"AI 배틀 결과 처리 중 예상치 못한 오류 발생: {e}")
        return {"error": f"AI 배틀 분석 중 예상치 못한 내부 오류가 발생했습니다: {e}"}

scheduler = BackgroundScheduler()

def perform_random_battle():
    print("\n--- 1분마다 자동 배틀 시작 ---")

    try:
        response = requests.get(f"{PHP_API_BASE_URL}/get_characters.php", timeout=10)
        response.raise_for_status()
        characters_data = response.json()
        
        if not characters_data or len(characters_data) < 2:
            print("캐릭터가 2명 미만이므로 자동 배틀을 건너킵니다.")
            return

        characters = [
            type('Character', (object,), char_dict) for char_dict in characters_data
        ]
        
    except requests.exceptions.RequestException as e:
        print(f"자동 배틀: 캐릭터 목록을 가져오는 중 오류 발생 (PHP API): {e}")
        return

    char1, char2 = random.sample(characters, 2)
    
    print(f"자동 배틀: {char1.name} vs {char2.name}")

    battle_results = get_ai_battle_response(
        char1.name, char1.description,
        char2.name, char2.description
    )

    if "error" in battle_results:
        print(f"자동 배틀 실패: {battle_results['error']}")
        return

    winner_name = battle_results['winner']
    loser_name = battle_results['loser']
    reason = battle_results['reason']

    winner_char_id = None
    loser_char_id = None

    if winner_name == char1.name and loser_name == char2.name:
        winner_char_id = char1.id
        loser_char_id = char2.id
    elif winner_name == char2.name and loser_name == char1.name:
        winner_char_id = char2.id
        loser_char_id = char1.id
    else:
        print(f"경고: AI 응답의 승자/패자 이름이 참가 캐릭터와 일치하지 않습니다.")
        print(f"AI 응답: 승자='{winner_name}', 패자='{loser_name}'")
        print(f"참가 캐릭터: '{char1.name}', '{char2.name}'")
        return

    try:
        update_winner_response = requests.post(
            f"{PHP_API_BASE_URL}/update_character_stats.php",
            json={"id": winner_char_id, "type": "win"},
            timeout=10
        )
        update_winner_response.raise_for_status()

        update_loser_response = requests.post(
            f"{PHP_API_BASE_URL}/update_character_stats.php",
            json={"id": loser_char_id, "type": "loss"},
            timeout=10
        )
        update_loser_response.raise_for_status()
        
        print(f"자동 배틀 완료: {winner_name} 승리! ({reason})")

    except requests.exceptions.RequestException as e:
        print(f"자동 배틀: 승패 기록 업데이트 중 오류 발생 (PHP API): {e}")
        return

    try:
        log_battle_response = requests.post(
            f"{PHP_API_BASE_URL}/log_battle.php",
            json={
                "character1_id": char1.id,
                "character2_id": char2.id,
                "winner_id": winner_char_id,
                "loser_id": loser_char_id,
                "battle_reason": reason
            },
            timeout=10
        )
        log_battle_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"자동 배틀: 배틀 로그 저장 중 오류 발생 (PHP API): {e}")
        return

scheduler.add_job(perform_random_battle, 'interval', minutes= 1)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/character-creator')
def character_creator():
    return render_template('index.html')

@app.route('/ranking')
def ranking_page():
    return render_template('ranking.html')

@app.route('/rules') 
def rules_page():
    return render_template('rule.html')

@app.route('/api/ranking')
def get_ranking():

    try:
        response = requests.get(f"{PHP_API_BASE_URL}/get_ranking.php", timeout=10)
        response.raise_for_status()
        ranking_data = response.json()
        return jsonify(ranking_data)
    except requests.exceptions.RequestException as e:
        print(f"랭킹 데이터를 가져오는 중 오류 발생 (PHP API): {e}")
        return jsonify({"error": f"랭킹 데이터를 불러오는 데 실패했습니다: {e}"}), 500


@app.route('/analyze_character', methods=['POST'])
def analyze_character():
    data = request.get_json()

    character_name = data.get('name')
    character_description = data.get('description')

    if not character_name or not character_description:
        return jsonify({"error": "캐릭터 이름과 설명을 모두 제공해야 합니다."}), 400

    name_profanity = check_profanity(character_name, FORBIDDEN_WORDS)
    desc_profanity = check_profanity(character_description, FORBIDDEN_WORDS)

    if name_profanity or desc_profanity:
        profane_words = ", ".join(set(name_profanity + desc_profanity))
        return jsonify({"error": f"사용할 수 없는 단어가 포함되어 있습니다: {profane_words}"}), 400

    try:
        check_duplicate_response = requests.get(
            f"{PHP_API_BASE_URL}/get_characters.php?name={character_name}",
            timeout=10
        )
        check_duplicate_response.raise_for_status()
        existing_chars = check_duplicate_response.json()
        if existing_chars:
            return jsonify({"error": f"'{character_name}' 이름의 캐릭터가 이미 존재합니다. 다른 이름을 사용해주세요."}), 409
    except requests.exceptions.RequestException as e:
        print(f"캐릭터 이름 중복 확인 중 오류 발생 (PHP API): {e}")
        return jsonify({"error": f"캐릭터 이름 중복 확인 중 오류 발생: {e}"}), 500

    ai_analysis_prompt = f"""
    당신은 사용자 캐릭터를 분석하는 AI입니다.
    사용자가 제공하는 캐릭터 정보를 바탕으로 캐릭터의 특징, 능력, 강점, 약점 등을 상세히 분석하여 설명해주세요.
    추가 설명이나 인사말 없이 순수하게 분석 내용만 출력하세요.

    ---
    사용자 캐릭터 이름: {character_name}
    사용자 캐릭터 소개: {character_description}
    ---

    출력 형식:
    캐릭터_설명: [캐릭터 분석 내용]
    """
    
    try:
        response = model.generate_content(ai_analysis_prompt, safety_settings=SAFETY_SETTINGS)
        ai_output = response.text
        print(f"\n--- Gemini Character Analysis Raw Output (for '{character_name}') ---")
        print(ai_output)
        print("----------------------------------------\n")

        parsed_analysis = {}
        if '캐릭터_설명:' in ai_output:
            parsed_analysis['캐릭터_설명'] = ai_output.split('캐릭터_설명:', 1)[1].strip()
        else:
            parsed_analysis['캐릭터_설명'] = ai_output.strip()

        character_ai_analysis = parsed_analysis.get('캐릭터_설명', 'AI 분석 결과를 받아오지 못했습니다.')
        if character_ai_analysis == 'AI 분석 결과를 받아오지 못했습니다.' or not character_ai_analysis:
            raise ValueError("Gemini가 캐릭터 설명을 제대로 생성하지 못했습니다.")

    except genai.types.BlockedPromptException as e:
        print(f"Gemini API 오류: 캐릭터 분석 프롬프트가 차단되었습니다. - {e.response.prompt_feedback.block_reason}")
        return jsonify({"error": "캐릭터 분석 중 부적절한 내용이 감지되어 차단되었습니다."}), 500
    except exceptions.GoogleAPIError as e:
        print(f"Gemini API 호출 중 오류 발생 (GoogleAPIError): {e}")
        return jsonify({"error": f"AI 분석 서비스와 통신 중 오류가 발생했습니다: {e}"}), 500
    except Exception as e:
        print(f"캐릭터 분석 중 예상치 못한 오류 발생: {e}")
        return jsonify({"error": f"캐릭터 분석 중 내부 오류가 발생했습니다: {e}"}), 500

    try:
        save_response = requests.post(
            f"{PHP_API_BASE_URL}/save_character.php",
            json={
                "name": character_name,
                "description": character_description,
                "ai_analysis": character_ai_analysis,
                "wins": 0,  
                "losses": 0 
            },
            timeout=10
        )
        save_response.raise_for_status() 

        php_response_data = save_response.json()
        if not php_response_data.get('success'):
            raise Exception(f"PHP 저장 실패: {php_response_data.get('message', '알 수 없는 오류')}")
        
        print(f"캐릭터 '{character_name}'이(가) PHP를 통해 데이터베이스에 성공적으로 추가되었습니다.")
    except requests.exceptions.RequestException as e:
        print(f"경고: PHP 저장 서버 통신 오류: {e}")
        return jsonify({"error": f"캐릭터 정보를 저장할 수 없습니다. PHP 서버 통신 오류: {e}", "character_analysis": character_ai_analysis}), 500
    except Exception as e:
        print(f"경고: PHP 저장 엔드포인트 호출 중 예상치 못한 오류 발생: {e}")
        return jsonify({"error": f"캐릭터 정보 저장 중 예상치 못한 오류 발생: {e}", "character_ai_analysis": character_ai_analysis}), 500

    return jsonify({
        "character_analysis": character_ai_analysis,
        "message": f"'{character_name}' 캐릭터가 성공적으로 생성되었습니다. 이제 자동 배틀에 참여합니다!"
    })


if __name__ == '__main__':
    scheduler.start()
    print("자동 배틀 스케줄러가 시작되었습니다.")

    atexit.register(lambda: scheduler.shutdown())

    app.run(host='0.0.0.0', port=5000, debug=True)
