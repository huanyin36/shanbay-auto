"""
扇贝单词自动刷词 v3 - 纯 API 版
无需浏览器，直接从 Edge 提取 cookie 调用 API，2秒刷完40词。

依赖: pip install rookiepy requests
用法: python shanbay.py

功能增强:
- 每日首次运行检测任务状态，完成后当天不再重复检测
- 每周自动清理一次日志文件
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import rookiepy
import requests

# 配置路径
SCRIPT_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCRIPT_DIR / ".shanbay_state.json"
LOG_FILE = SCRIPT_DIR / "shanbay.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_state():
    """加载本地状态文件"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"last_check_date": None, "today_completed": False, "last_log_cleanup": None}


def save_state(state):
    """保存本地状态文件"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


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
                    except:
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


def get_session():
    """从 Edge 浏览器提取扇贝 cookie，构建请求会话"""
    cookies = rookiepy.edge(domains=[".shanbay.com"])
    if not cookies:
        logger.error("[-] 未找到扇贝 cookie，请先在 Edge 中登录 web.shanbay.com")
        sys.exit(1)

    jar = {c["name"]: c["value"] for c in cookies}
    csrf = jar.get("csrftoken", "")

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
    r = s.get("https://apiv3.shanbay.com/wordsapp/user_material_books/current")
    data = r.json()
    # 尝试从 learning_task_id 或 materialbook 中获取
    book_id = data.get("materialbook", {}).get("book_id") or data.get("learning_task_id", "segle")
    return book_id


def complete_daily(s, book_id="segle"):
    """完成每日背词任务"""
    base = f"https://apiv3.shanbay.com/wordsapp/user_material_books/{book_id}/learning"

    # 1. 检查状态
    r = s.get(f"{base}/statuses")
    status = r.json()
    if status.get("is_finished"):
        logger.info("[+] 今日任务已完成，无需操作")
        return True

    total = status.get("a_count", 0) + status.get("c_count", 0)
    logger.info(f"[*] 今日任务：{status.get('a_count', 0)} 新词 + {status.get('c_count', 0)} 复习")

    # 2. 获取待学词条
    r = s.get(f"{base}/items/sync")
    data = r.json()
    a_items = data.get("a_not_finished_items", [])
    c_items = data.get("c_not_finished_items", [])

    if not a_items and not c_items:
        logger.info("[+] 没有待学词条")
        return True

    def to_item(i):
        return {"item_id": i["item_id"], "schedule": i["schedule"], "failed_count": i["failed_count"]}

    # 3. 全部标记为"认识"提交
    body = {
        "a_items": [],
        "a_items_known": [to_item(i) for i in a_items],
        "c_items": [],
        "c_items_known": [to_item(i) for i in c_items],
        "date": status.get("date", ""),
        "learning_time": max(total * 3, 60),  # 模拟学习时间
    }

    r = s.put(f"{base}/items/sync", json=body)
    if r.status_code == 200:
        logger.info(f"[+] 完成！{len(a_items)} 新词 + {len(c_items)} 复习，全部标记为认识")
        return True
    else:
        logger.error(f"[-] 提交失败：{r.status_code} {r.text[:200]}")
        return False


def main():
    logger.info("[*] 扇贝单词自动刷词 v3 (API)")
    
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
