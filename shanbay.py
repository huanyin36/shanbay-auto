r"""
扇贝单词自动刷词 v4 - CDP + API 版
通过 Chrome DevTools Protocol 从 Edge 提取 cookie，调用 API 完成刷词。
解决了新版 Edge cookie 加密格式变化导致 rookiepy 无法解密的问题。

依赖: pip install requests websocket-client
用法: python shanbay.py

功能增强:
- 每日首次运行检测任务状态，完成后当天不再重复检测
- 每周自动清理一次日志文件

配置说明:
- 可通过环境变量 SHANBAY_EDGE_USER_DATA_DIR / SHANBAY_EDGE_DISK_CACHE_DIR 自定义 Edge 用户数据目录与缓存目录；未设置时默认使用 Edge 自身配置（标准安装开箱即用），仅便携版等需自定义路径时再设置
"""

import sys
import os
import json
import logging
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests
import websocket

# 配置路径
SCRIPT_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCRIPT_DIR / ".shanbay_state.json"
LOG_FILE = SCRIPT_DIR / "shanbay.log"

# Edge 用户数据目录与缓存目录：默认不指定，使用 Edge 自身默认配置（标准安装开箱即用）；
# 仅当设置了对应环境变量时才显式追加 --user-data-dir / --disk-cache-dir（便携版 Edge 等场景）。
EDGE_USER_DATA_DIR = os.environ.get("SHANBAY_EDGE_USER_DATA_DIR")
EDGE_DISK_CACHE_DIR = os.environ.get("SHANBAY_EDGE_DISK_CACHE_DIR")

# 配置日志 - 自定义过滤器以脱敏敏感信息
class SensitiveDataFilter(logging.Filter):
    """过滤日志中的敏感数据"""
    def filter(self, record):
        # 对消息进行脱敏处理
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # 移除或替换可能的 CSRF token 和 cookie 值
            record.msg = re.sub(r'csrftoken=[a-zA-Z0-9]+', 'csrftoken=***', record.msg)
            record.msg = re.sub(r'"csrftoken":\s*"[a-zA-Z0-9]+"', '"csrftoken": "***"', record.msg)
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())


def load_state():
    """加载本地状态文件"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"状态文件读取失败：{e}")
            pass
    return {"last_check_date": None, "today_completed": False, "last_log_cleanup": None}


def save_state(state):
    """保存本地状态文件"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        # 设置文件权限为仅所有者可读写 (Unix 系统)
        if os.name != 'nt':  # 非 Windows 系统
            os.chmod(STATE_FILE, 0o600)
    except IOError as e:
        logger.error(f"状态文件写入失败：{e}")


def cleanup_old_logs():
    """清理超过7天的日志"""
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 检查是否需要清理（每周一次）
    last_cleanup = state.get("last_log_cleanup")
    if last_cleanup:
        last_date = datetime.strptime(last_cleanup, "%Y-%m-%d")
        if (datetime.now() - last_date).days < 7:
            return
    
    if not LOG_FILE.exists():
        return
    
    try:
        # 读取日志，保留最近7天的内容
        cutoff_date = datetime.now() - timedelta(days=7)
        lines_to_keep = []
        
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    # 尝试解析日志时间戳
                    try:
                        log_date_str = line.split()[0] + " " + line.split()[1]
                        log_date = datetime.strptime(log_date_str, "%Y-%m-%d %H:%M:%S,%f")
                        if log_date >= cutoff_date:
                            lines_to_keep.append(line)
                    except (ValueError, IndexError):
                        # 无法解析的行也保留
                        lines_to_keep.append(line)
        
        # 写回过滤后的日志
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines_to_keep)
        
        state["last_log_cleanup"] = today
        save_state(state)
        logger.info("[+] 日志清理完成，已删除7天前的记录")
    except Exception as e:
        logger.error(f"[-] 日志清理失败：{e}")


def find_edge_exe():
    """查找 Edge 可执行文件路径"""
    # 1. 便携版常见路径
    for pattern in [r"D:\Edge\Edge\*\msedge.exe", r"D:\Edge\*\msedge.exe"]:
        from glob import glob
        matches = glob(pattern)
        if matches:
            return matches[0]

    # 2. 注册表（junction / 标准安装）
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
        path = winreg.QueryValue(key, None)
        winreg.CloseKey(key)
        if path and os.path.isfile(path):
            return path
    except Exception:
        pass

    # 3. 标准路径
    for env_var in ["PROGRAMFILES", "PROGRAMFILES(X86)"]:
        p = os.path.join(os.environ.get(env_var, ""), r"Microsoft\Edge\Application\msedge.exe")
        if os.path.isfile(p):
            return p

    return None


def ensure_debug_port(port=9222):
    """确保 Edge 开启了远程调试端口"""
    # 已经开了？
    try:
        r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
        if r.ok:
            return True
    except Exception:
        pass

    edge_exe = find_edge_exe()
    if not edge_exe:
        logger.error("[-] 找不到 Edge 浏览器")
        return False

    # 启动 Edge 并附加调试端口。
    # 默认不指定 user-data-dir / disk-cache-dir，让 Edge 使用自身默认用户配置（标准安装开箱即用）。
    # 仅当设置了 SHANBAY_EDGE_USER_DATA_DIR / SHANBAY_EDGE_DISK_CACHE_DIR 时才追加对应参数，
    # 以便便携版 Edge 等自定义场景使用。
    edge_args = [
        edge_exe,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if EDGE_USER_DATA_DIR:
        edge_args.append(f"--user-data-dir={EDGE_USER_DATA_DIR}")
    if EDGE_DISK_CACHE_DIR:
        edge_args.append(f"--disk-cache-dir={EDGE_DISK_CACHE_DIR}")
    subprocess.Popen(edge_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 等待端口就绪
    for _ in range(20):
        time.sleep(1)
        try:
            r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
            if r.ok:
                return True
        except Exception:
            continue

    logger.error("[-] Edge 调试端口启动超时")
    return False


def get_cookies_via_cdp(port=9222):
    """通过 CDP 从 Edge 提取扇贝 cookie"""
    try:
        pages = requests.get(f"http://127.0.0.1:{port}/json", timeout=5).json()
    except Exception as e:
        logger.error(f"[-] 无法连接 Edge 调试端口：{e}")
        return {}

    if not pages:
        logger.error("[-] Edge 没有打开的页面")
        return {}

    # 用第一个页面获取 cookie
    ws_url = pages[0]["webSocketDebuggerUrl"]
    ws = websocket.WebSocket()
    ws.connect(ws_url, suppress_origin=True)

    ws.send(json.dumps({
        "id": 1,
        "method": "Network.getCookies",
        "params": {"urls": ["https://web.shanbay.com", "https://apiv3.shanbay.com"]}
    }))

    resp = json.loads(ws.recv())
    ws.close()

    if "result" not in resp:
        logger.error(f"[-] CDP 返回错误：{resp.get('error')}")
        return {}

    cookies = {}
    for c in resp["result"].get("cookies", []):
        if "shanbay" in c.get("domain", ""):
            cookies[c["name"]] = c["value"]

    return cookies


def get_session():
    """从 Edge 浏览器提取扇贝 cookie，构建请求会话"""
    if not ensure_debug_port():
        sys.exit(1)

    jar = get_cookies_via_cdp()
    if not jar:
        logger.error("[-] 未找到扇贝 cookie，请先在 Edge 中登录 web.shanbay.com")
        sys.exit(1)

    csrf = jar.get("csrftoken", "")
    if not csrf:
        logger.error("[-] 未找到 CSRF token，请检查 cookie 是否有效")
        sys.exit(1)

    s = requests.Session()
    s.cookies.update(jar)
    s.headers.update({
        "X-CSRFToken": csrf,
        "Content-Type": "application/json",
        "Referer": "https://web.shanbay.com/wordsweb/",
        "Origin": "https://web.shanbay.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
    })
    return s


def get_book_id(s):
    """获取当前词书的 API 路径标识（如 segal/cet4 等短码）"""
    try:
        r = s.get("https://apiv3.shanbay.com/wordsapp/user_material_books/current", timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # 验证响应数据结构
        if not isinstance(data, dict):
            logger.error("[-] API 返回数据格式错误：非字典类型")
            return "segle"
            
        # 词书短码在 materialbook_id（顶层）或 materialbook.id 中；
        # learning_task_id 是任务 id，不能用于 URL，否则会 404
        book_id = data.get("materialbook_id")
        if not book_id:
            materialbook = data.get("materialbook")
            if isinstance(materialbook, dict):
                book_id = materialbook.get("id")
        if not book_id:
            book_id = "segle"

        return book_id
    except requests.exceptions.RequestException as e:
        logger.error(f"[-] 获取词书 ID 失败：{e}")
        return "segle"
    except json.JSONDecodeError as e:
        logger.error(f"[-] 解析 API 响应失败：{e}")
        return "segle"


def complete_daily(s, book_id="segle"):
    """完成每日背词任务"""
    base = f"https://apiv3.shanbay.com/wordsapp/user_material_books/{book_id}/learning"

    try:
        # 1. 检查状态
        r = s.get(f"{base}/statuses", timeout=10)
        r.raise_for_status()
        status = r.json()
        
        if not isinstance(status, dict):
            logger.error("[-] 状态响应格式错误")
            return False
            
        if status.get("is_finished"):
            logger.info("[+] 今日任务已完成，无需操作")
            return True

        total = status.get("a_count", 0) + status.get("c_count", 0)
        logger.info(f"[*] 今日任务：{status.get('a_count', 0)} 新词 + {status.get('c_count', 0)} 复习")

        # 2. 获取待学词条
        r = s.get(f"{base}/items/sync", timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if not isinstance(data, dict):
            logger.error("[-] 词条同步响应格式错误")
            return False
            
        a_items = data.get("a_not_finished_items", [])
        c_items = data.get("c_not_finished_items", [])

        if not a_items and not c_items:
            logger.info("[+] 没有待学词条")
            return True

        def to_item(i):
            if not isinstance(i, dict) or "item_id" not in i:
                return None
            return {"item_id": i["item_id"], "schedule": i.get("schedule", 0), "failed_count": i.get("failed_count", 0)}

        # 3. 全部标记为"认识"提交
        body = {
            "a_items": [],
            "a_items_known": [to_item(i) for i in a_items if to_item(i)],
            "c_items": [],
            "c_items_known": [to_item(i) for i in c_items if to_item(i)],
            "date": status.get("date", ""),
            "learning_time": max(total * 3, 60),  # 模拟学习时间
        }

        r = s.put(f"{base}/items/sync", json=body, timeout=10)
        if r.status_code == 200:
            logger.info(f"[+] 完成！{len(a_items)} 新词 + {len(c_items)} 复习，全部标记为认识")
            return True
        else:
            logger.error(f"[-] 提交失败：{r.status_code} {r.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"[-] 网络请求失败：{e}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"[-] JSON 解析失败：{e}")
        return False
    except (KeyError, TypeError) as e:
        logger.error(f"[-] 数据处理错误：{e}")
        return False


def main():
    logger.info("[*] 扇贝单词自动刷词 v4 (CDP+API)")
    
    # 1. 先清理旧日志（每周一次）
    cleanup_old_logs()
    
    # 2. 加载状态
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 3. 检查今天是否已经执行过
    if state.get("last_check_date") == today and state.get("today_completed"):
        logger.info("[*] 今日已执行过检测，跳过")
        return
    
    # 4. 执行任务
    s = get_session()
    logger.info("[+] Cookie 有效")
    book_id = get_book_id(s)
    success = complete_daily(s, book_id=book_id)
    
    # 5. 更新状态
    if success:
        state["last_check_date"] = today
        state["today_completed"] = True
        save_state(state)
        logger.info("[*] 状态已更新，今日不再重复检测")


if __name__ == "__main__":
    main()
