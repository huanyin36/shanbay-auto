"""
扇贝单词自动刷词 v3 - 纯 API 版
无需浏览器，直接从 Edge 提取 cookie 调用 API，2秒刷完40词。

依赖: pip install rookiepy requests
用法: python shanbay.py
"""

import sys
import rookiepy
import requests


def get_session():
    """从 Edge 浏览器提取扇贝 cookie，构建请求会话"""
    cookies = rookiepy.edge(domains=[".shanbay.com"])
    if not cookies:
        print("[-] 未找到扇贝 cookie，请先在 Edge 中登录 web.shanbay.com")
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
        print("[+] 今日任务已完成，无需操作")
        return True

    total = status.get("a_count", 0) + status.get("c_count", 0)
    print(f"[*] 今日任务: {status.get('a_count', 0)} 新词 + {status.get('c_count', 0)} 复习")

    # 2. 获取待学词条
    r = s.get(f"{base}/items/sync")
    data = r.json()
    a_items = data.get("a_not_finished_items", [])
    c_items = data.get("c_not_finished_items", [])

    if not a_items and not c_items:
        print("[+] 没有待学词条")
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
        print(f"[+] 完成！{len(a_items)} 新词 + {len(c_items)} 复习，全部标记为认识")
        return True
    else:
        print(f"[-] 提交失败: {r.status_code} {r.text[:200]}")
        return False


def main():
    print("[*] 扇贝单词自动刷词 v3 (API)")
    s = get_session()
    print("[+] Cookie 有效")
    book_id = get_book_id(s)
    complete_daily(s, book_id=book_id)


if __name__ == "__main__":
    main()
