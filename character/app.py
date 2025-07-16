from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests
from google.api_core import exceptions
from apscheduler.schedulers.background import BackgroundScheduler
import random
import atexit
import pymysql
import time
import re

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

FORBIDDEN_WORDS = ["반드시","절대","무조건","불사","어머니","애미","아버지","아빠","엄마","본경","석열","노무현","재명","부엉이","노알라","게이","이긴","이김","이겨","지지","패배", "승리", "무한", "계속", "다솔", "인지", "정연", "선아", "운지", "북딱", "일베", "디씨", "자지", "고추", "꼬추", "섹스", "ㅅㅅ", ]

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "your_character_db")

def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except pymysql.Error as e:
        print(f"데이터베이스 연결 실패: {e}")
        raise

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    SQL 쿼리를 실행하고 결과를 반환합니다.
    :param query: 실행할 SQL 쿼리 문자열
    :param params: 쿼리에 바인딩할 파라미터 튜플 또는 리스트
    :param fetch_one: 하나의 결과만 가져올지 여부
    :param fetch_all: 모든 결과를 가져올지 여부
    :return: 쿼리 결과 (딕셔너리 또는 딕셔너리 리스트)
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid
    except pymysql.Error as e:
        print(f"SQL 쿼리 실행 오류: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def check_profanity(text, forbidden_words):
    """텍스트에 금칙어가 포함되어 있는지 확인합니다."""
    found_words = []
    text_lower = text.lower()
    for word in forbidden_words:
        if word.lower() in text_lower:
            found_words.append(word)
    return found_words

def get_ai_battle_response(character1_name, character1_desc, character2_name, character2_desc):
    """Gemini AI를 사용하여 두 캐릭터 간의 배틀 결과를 예측합니다."""
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
        승자: [승자 캐릭터의 정확한 전체 이름 (괄호 안의 정보 포함)]
        패자: [패자 캐릭터의 정확한 전체 이름 (괄호 안의 정보 포함)]
        판단_근거: [승패에 대한 상세한 이유]
        예시:
        승자: 김독자
        패자: 논개(30611)
        판단_근거: 김독자는 논개(30611)의 능력을 무력화할 수 있습니다.
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

global scheduler
scheduler = None

def perform_random_battle():
    """정기적으로 무작위 캐릭터 두 명을 선택하여 배틀을 수행합니다."""
    print("\n--- 0.5분마다 자동 배틀 시작 ---")

    try:
        characters_data = execute_query("SELECT id, name, description, (wins + losses) AS total_battles FROM characters", fetch_all=True)
        
        if not characters_data or len(characters_data) < 2:
            print("캐릭터가 2명 미만이므로 자동 배틀을 건너낍니다.")
            return

        characters_data.sort(key=lambda x: x['total_battles'])
        num_candidates = max(2, min(len(characters_data), len(characters_data) // 2 + 1)) 
        
        eligible_characters = characters_data[:num_candidates]

        for i in range(2):
            if len(eligible_characters) < 2:
                print(f"충분한 캐릭터가 없어 {i+1}번째 배틀을 건너뜁니다.")
                break

            char1, char2 = random.sample(eligible_characters, 2)
            char1_name_for_ai = char1['name']
            char2_name_for_ai = char2['name']

            print(f"자동 배틀 ({i+1}/2): {char1['name']} vs {char2['name']}")

            battle_results = get_ai_battle_response(
                char1_name_for_ai, char1['description'],
                char2_name_for_ai, char2['description']
            )

            if "error" in battle_results:
                print(f"자동 배틀 ({i+1}/2) 실패: {battle_results['error']}")
                continue 

            winner_name_from_ai = battle_results['winner']
            loser_name_from_ai = battle_results['loser']
            reason = battle_results['reason']

            winner_char_id = None
            loser_char_id = None

            if winner_name_from_ai == char1['name']:
                winner_char_id = char1['id']
            elif winner_name_from_ai == char2['name']:
                winner_char_id = char2['id']

            if loser_name_from_ai == char1['name']:
                loser_char_id = char1['id']
            elif loser_name_from_ai == char2['name']:
                loser_char_id = char2['id']

            if winner_char_id is None and len(winner_name_from_ai) > 0:
                if char1['name'].startswith(winner_name_from_ai):
                    winner_char_id = char1['id']
                elif char2['name'].startswith(winner_name_from_ai):
                    winner_char_id = char2['id']
            
            if loser_char_id is None and len(loser_name_from_ai) > 0:
                if char1['name'].startswith(loser_name_from_ai):
                    loser_char_id = char1['id']
                elif char2['name'].startswith(loser_name_from_ai):
                    loser_char_id = char2['id']

            if winner_char_id is None or loser_char_id is None:
                print(f"경고: AI 응답의 승자/패자 이름이 참가 캐릭터와 일치하지 않습니다. (ID 불일치)")
                print(f"AI 응답: 승자='{winner_name_from_ai}', 패자='{loser_name_from_ai}'")
                print(f"참가 캐릭터 (원본): '{char1['name']}', '{char2['name']}'")
                print(f"참가 캐릭터 (AI 전달용): '{char1_name_for_ai}', '{char2_name_for_ai}'")
                continue 

            try:
                execute_query("UPDATE characters SET wins = wins + 1 WHERE id = %s", (winner_char_id,))
                execute_query("UPDATE characters SET losses = losses + 1 WHERE id = %s", (loser_char_id,))
                
                print(f"자동 배틀 ({i+1}/2) 완료: {winner_name_from_ai} 승리! ({reason})")

            except Exception as e:
                print(f"자동 배틀 ({i+1}/2): 승패 기록 업데이트 중 오류 발생: {e}")
                continue 

            try:
                execute_query(
                    "INSERT INTO battle_logs (character1_id, character2_id, winner_id, loser_id, battle_reason) VALUES (%s, %s, %s, %s, %s)",
                    (char1['id'], char2['id'], winner_char_id, loser_char_id, reason)
                )
            except Exception as e:
                print(f"자동 배틀 ({i+1}/2): 배틀 로그 저장 중 오류 발생: {e}")
                continue

            if i == 0:
                time.sleep(1)

    except Exception as e:
        print(f"자동 배틀 전체 실행 중 오류 발생: {e}")
        return

def initialize_scheduler():
    global scheduler
    
    if scheduler is not None:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
            print("Existing scheduler instance shutdown for re-initialization.")
        except Exception as e:
            print(f"Error during existing scheduler shutdown: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(perform_random_battle, 'interval', minutes=0.5, id='random_battle_job', replace_existing=True)
    scheduler.start()
    print("AI 스케줄러가 새로 초기화되고 시작되었습니다.")

    atexit.register(lambda: scheduler.shutdown())

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
        ranking_data = execute_query("""
            SELECT 
                id, 
                name, 
                wins, 
                losses, 
                (wins + losses) AS total_battles,
                ROUND(IFNULL((wins / (wins + losses)) * 100, 0), 2) AS win_rate
            FROM characters
            ORDER BY win_rate DESC, wins DESC, total_battles DESC, name ASC
        """, fetch_all=True)

        if ranking_data:
            for i, char in enumerate(ranking_data):
                char['rank'] = i + 1
        
        return jsonify(ranking_data)
    except Exception as e:
        print(f"랭킹 데이터를 가져오는 중 오류 발생: {e}")
        return jsonify({"error": f"랭킹 데이터를 불러오는 데 실패했습니다: {e}"}), 500

@app.route('/api/save_character', methods=['POST'])
def save_character_flask():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    ai_analysis = data.get('ai_analysis')
    wins = data.get('wins', 0)
    losses = data.get('losses', 0)

    if not name or not description or not ai_analysis:
        return jsonify({"success": False, "message": "필수 데이터가 누락되었습니다."}), 400

    try:
        query = "INSERT INTO characters (name, description, ai_analysis, wins, losses) VALUES (%s, %s, %s, %s, %s)"
        character_id = execute_query(query, (name, description, ai_analysis, wins, losses))
        return jsonify({"success": True, "message": "캐릭터가 성공적으로 저장되었습니다.", "id": character_id}), 201
    except pymysql.err.IntegrityError as e:
        if "Duplicate entry" in str(e):
            return jsonify({"success": False, "message": f"'{name}' 이름의 캐릭터가 이미 존재합니다."}), 409
        return jsonify({"success": False, "message": f"데이터베이스 저장 오류: {e}"}), 500
    except Exception as e:
        print(f"캐릭터 저장 중 오류 발생: {e}")
        return jsonify({"success": False, "message": f"서버 오류: {e}"}), 500

@app.route('/api/characters')
def get_characters_flask():
    character_name = request.args.get('name')
    try:
        if character_name:
            query = "SELECT id, name, description, ai_analysis, wins, losses FROM characters WHERE name = %s"
            characters = execute_query(query, (character_name,), fetch_all=True)
        else:
            query = "SELECT id, name, description, ai_analysis, wins, losses FROM characters"
            characters = execute_query(query, fetch_all=True)
        return jsonify(characters)
    except Exception as e:
        print(f"캐릭터 목록/조회 중 오류 발생: {e}")
        return jsonify({"error": f"캐릭터 데이터를 불러오는 데 실패했습니다: {e}"}), 500

@app.route('/api/update_character_stats', methods=['POST'])
def update_character_stats_flask():
    data = request.get_json()
    character_id = data.get('id')
    update_type = data.get('type')

    if not character_id or update_type not in ['win', 'loss']:
        return jsonify({"success": False, "message": "유효하지 않은 요청입니다."}), 400

    try:
        if update_type == 'win':
            query = "UPDATE characters SET wins = wins + 1 WHERE id = %s"
        else:
            query = "UPDATE characters SET losses = losses + 1 WHERE id = %s"
        execute_query(query, (character_id,))
        return jsonify({"success": True, "message": "스탯 업데이트 성공"}), 200
    except Exception as e:
        print(f"캐릭터 스탯 업데이트 중 오류 발생: {e}")
        return jsonify({"success": False, "message": f"서버 오류: {e}"}), 500

@app.route('/api/log_battle', methods=['POST'])
def log_battle_flask():
    data = request.get_json()
    char1_id = data.get('character1_id')
    char2_id = data.get('character2_id')
    winner_id = data.get('winner_id')
    loser_id = data.get('loser_id')
    reason = data.get('battle_reason')

    if not all([char1_id, char2_id, winner_id, loser_id, reason]):
        return jsonify({"success": False, "message": "필수 배틀 로그 데이터가 누락되었습니다."}), 400

    try:
        query = "INSERT INTO battle_logs (character1_id, character2_id, winner_id, loser_id, battle_reason) VALUES (%s, %s, %s, %s, %s)"
        execute_query(query, (char1_id, char2_id, winner_id, loser_id, reason))
        return jsonify({"success": True, "message": "배틀 로그 저장 성공"}), 201
    except Exception as e:
        print(f"배틀 로그 저장 중 오류 발생: {e}")
        return jsonify({"success": False, "message": f"서버 오류: {e}"}), 500

@app.route('/api/latest_battle_log')
def get_latest_battle_log_flask():
    try:
        query = """
            SELECT 
                bl.timestamp,
                bl.battle_reason,
                c1.name AS character1_name,
                c2.name AS character2_name,
                w.name AS winner_name,
                l.name AS loser_name
            FROM battle_logs bl
            JOIN characters c1 ON bl.character1_id = c1.id
            JOIN characters c2 ON bl.character2_id = c2.id
            JOIN characters w ON bl.winner_id = w.id
            JOIN characters l ON bl.loser_id = l.id
            ORDER BY bl.timestamp DESC
            LIMIT 1
        """
        latest_battle = execute_query(query, fetch_one=True)
        return jsonify(latest_battle if latest_battle else {})
    except Exception as e:
        print(f"최신 배틀 로그 가져오는 중 오류 발생: {e}")
        return jsonify({"error": f"서버 오류: {e}"}), 500

@app.route('/api/character_battles/<int:character_id>')
def get_character_battles_flask(character_id):
    try:
        query = """
            SELECT
                bl.timestamp,
                bl.battle_reason,
                c1.name AS character1_name,
                c2.name AS character2_name,
                w.name AS winner_name,
                l.name AS loser_name
            FROM battle_logs bl
            JOIN characters c1 ON bl.character1_id = c1.id
            JOIN characters c2 ON bl.character2_id = c2.id
            JOIN characters w ON bl.winner_id = w.id
            JOIN characters l ON bl.loser_id = l.id
            WHERE bl.character1_id = %s OR bl.character2_id = %s
            ORDER BY bl.timestamp DESC
        """
        battles = execute_query(query, (character_id, character_id), fetch_all=True)
        return jsonify(battles)
    except Exception as e:
        print(f"캐릭터 전적 가져오는 중 오류 발생: {e}")
        return jsonify({"error": f"서버 오류: {e}"}), 500

@app.route('/manager')
def manager_page():
    return render_template('manager.html')

@app.route('/api/admin/stop_scheduler', methods=['POST'])
def stop_scheduler():
    global scheduler
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            print("AI 스케줄러가 중단되었습니다.")
            return jsonify({"success": True, "message": "AI 스케줄러가 중단되었습니다."}), 200
        else:
            return jsonify({"success": False, "message": "AI 스케줄러가 이미 중단된 상태입니다."}), 200
    except Exception as e:
        print(f"스케줄러 중단 중 오류 발생: {e}")
        return jsonify({"success": False, "message": f"스케줄러 중단 실패: {e}"}), 500

@app.route('/api/admin/start_scheduler', methods=['POST'])
def start_scheduler():
    global scheduler
    try:
        if not (scheduler and scheduler.running):
            initialize_scheduler() 
            return jsonify({"success": True, "message": "AI 스케줄러가 시작되었습니다."}), 200
        else:
            return jsonify({"success": False, "message": "AI 스케줄러가 이미 실행 중입니다."}), 200
    except Exception as e:
        print(f"스케줄러 시작 중 오류 발생: {e}")
        return jsonify({"success": False, "message": f"스케줄러 시작 실패: {e}"}), 500

@app.route('/api/admin/scheduler_status', methods=['GET'])
def get_scheduler_status():
    global scheduler
    try:
        status = "running" if (scheduler and scheduler.running) else "stopped"
        return jsonify({"status": status, "message": f"AI 스케줄러가 현재 {status} 상태입니다."}), 200
    except Exception as e:
        print(f"스케줄러 상태 확인 중 오류 발생: {e}")
        return jsonify({"status": "unknown", "message": f"스케줄러 상태 확인 실패: {e}"}), 500

@app.route('/api/admin/delete_character', methods=['POST'])
def delete_character():
    data = request.get_json()
    character_id = data.get('id')

    if not character_id:
        return jsonify({"success": False, "message": "삭제할 캐릭터 ID가 필요합니다."}), 400

    try:
        delete_logs_query = """
            DELETE FROM battle_logs
            WHERE character1_id = %s OR character2_id = %s OR winner_id = %s OR loser_id = %s
        """
        execute_query(delete_logs_query, (character_id, character_id, character_id, character_id))

        delete_char_query = "DELETE FROM characters WHERE id = %s"
        rows_affected = execute_query(delete_char_query, (character_id,))

        if rows_affected > 0:
            print(f"캐릭터 ID {character_id} 및 관련 전적이 성공적으로 삭제되었습니다.")
            return jsonify({"success": True, "message": f"캐릭터 ID {character_id} 및 관련 전적이 성공적으로 삭제되었습니다."}), 200
        else:
            return jsonify({"success": False, "message": f"캐릭터 ID {character_id}를 찾을 수 없거나 이미 삭제되었습니다."}), 404
    except Exception as e:
        print(f"캐릭터 삭제 중 오류 발생: {e}")
        return jsonify({"success": False, "message": f"캐릭터 삭제 실패: {e}"}), 500


@app.route('/analyze_character', methods=['POST'])
def analyze_character():
    data = request.get_json()

    character_name = data.get('name')
    character_description = data.get('description')

    if not character_name or not character_description:
        return jsonify({"error": "캐릭터 이름과 설명을 모두 제공해야 합니다."}), 400

    name_pattern = re.compile(r'.+\(\d+\)$') 
    if not name_pattern.fullmatch(character_name):
        return jsonify({"error": "캐릭터 이름은 '이름(학번)' 형식이어야 합니다. (예: 홍길동(12345))"}), 400

    name_profanity = check_profanity(character_name, FORBIDDEN_WORDS)
    desc_profanity = check_profanity(character_description, FORBIDDEN_WORDS)

    if name_profanity or desc_profanity:
        profane_words = ", ".join(set(name_profanity + desc_profanity))
        return jsonify({"error": f"사용할 수 없는 단어가 포함되어 있습니다: {profane_words}"}), 400

    try:
        existing_chars = execute_query("SELECT id FROM characters WHERE name = %s", (character_name,), fetch_one=True)
        if existing_chars:
            return jsonify({"error": f"'{character_name}' 이름의 캐릭터가 이미 존재합니다. 다른 이름을 사용해주세요."}), 409
    except Exception as e:
        print(f"캐릭터 이름 중복 확인 중 오류 발생: {e}")
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
            f"{request.url_root.rstrip('/')}/api/save_character",
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
            raise Exception(f"캐릭터 저장 실패: {php_response_data.get('message', '알 수 없는 오류')}")
        
        print(f"캐릭터 '{character_name}'이(가) 데이터베이스에 성공적으로 추가되었습니다.")
    except requests.exceptions.RequestException as e:
        print(f"경고: 캐릭터 저장 API 통신 오류: {e}")
        return jsonify({"error": f"캐릭터 정보를 저장할 수 없습니다. API 통신 오류: {e}", "character_analysis": character_ai_analysis}), 500
    except Exception as e:
        print(f"경고: 캐릭터 저장 중 예상치 못한 오류 발생: {e}")
        return jsonify({"error": f"캐릭터 정보 저장 중 예상치 못한 오류 발생: {e}", "character_ai_analysis": character_ai_analysis}), 500

    return jsonify({
        "character_analysis": character_ai_analysis,
        "message": f"'{character_name}' 캐릭터가 성공적으로 생성되었습니다. 이제 자동 배틀에 참여합니다!"
    })


if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        initialize_scheduler()
    else:
        print("자동 배틀 스케줄러는 서브 프로세스에서 시작되지 않습니다. (리로더 프로세스)")

    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
