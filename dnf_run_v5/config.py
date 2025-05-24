import json
import requests
from pathlib import Path
from datetime import datetime
from utils import get_machine_code

def load_config():
    config_file = Path.home() / ".game_script_config" / "config.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
            else:
                print(f"配置文件 {config_file} 为空，跳过加载")
                return {}
    except FileNotFoundError:
        print(f"配置文件 {config_file} 不存在，跳过加载")
        return {}
    except json.JSONDecodeError as e:
        print(f"配置文件 {config_file} 格式错误: {e}，跳过加载")
        return {}
    except Exception as e:
        print(f"读取配置文件 {config_file} 时发生未知错误: {e}，跳过加载")
        return {}

def save_config(key, expiry_date, remember):
    config_file = Path.home() / ".game_script_config" / "config.json"
    config_dir = config_file.parent
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
    config = {
        'expire': expiry_date,
        'machine_code': get_machine_code(),
        'remember': remember
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)

def verify_key(key):
    machine_code = get_machine_code()
    try:
        response = requests.post(
            'http://139.196.94.227:5000/verify',
            json={'card': key, 'device_id': machine_code},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            message = data.get('message')
            expiry_date = data.get('expiry_date')
            if status == "success":
                expire_time = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                if expire_time > datetime.now():
                    return True, message, expiry_date
                else:
                    return False, "卡密已过期，请更换有效卡密", None
            else:
                return False, message, None
        else:
            error_msg = response.json().get('message', '未知错误')
            return False, f"服务器返回错误: {error_msg}", None
    except requests.exceptions.RequestException as e:
        return False, f"连接服务器失败: {str(e)}", None