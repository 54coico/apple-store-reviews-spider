import os
import csv
import time
import requests

#修改页数 "max_page": 10,
#每次只需要改ids就可以换别的app insta:389801252 outlook:951937596

# --- 配置区：无需 Authorization ---
config = {
    "max_page": 10,
    "ids": ["951937596"],
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0",
        "Origin": "https://apps.apple.com",
        "Referer": "https://apps.apple.com/",
        "Accept": "application/json",
    },
    "intervals": 3,
}

review_path = 'reviews'
if not os.path.exists(review_path):
    os.mkdir(review_path)

pending_queue = config['ids']
max_page = config['max_page']
headers = config['headers']
intervals = config['intervals']

def get_reviews(app_id, offset=0):
    """请求公开评论接口返回JSON；遇到429限流自动等待重试"""
    time.sleep(intervals)
    url = f'https://apps.apple.com/api/apps/v1/catalog/cn/apps/{app_id}/reviews' #写死了在中国大陆
    params = {
        "platform": "web",
        "limit": 20,
        "offset": offset,
        "sort": "recent",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 15))
            print(f"触发限流，等待 {wait} 秒后重试...")
            time.sleep(wait)
            return get_reviews(app_id, offset)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

def parse_reviews(data):
    """提取评论字段"""
    items = []
    for item in data.get("data", []):
        attr = item.get("attributes", {})
        items.append({
            "id": item.get("id", ""),
            "title": attr.get("title", ""),
            "userName": attr.get("userName", ""),
            "review": attr.get("review", ""),
            "rating": attr.get("rating", ""),
            "date": attr.get("date", ""),
            "isEdited": attr.get("isEdited", False),
        })
    return items

def main():
    while pending_queue:
        cur_id = pending_queue.pop()
        print(f'开始爬取 App ID: {cur_id}')
        all_items = []

        for page in range(max_page):
            data = get_reviews(cur_id, offset=page * 20)
            if not data:
                print(f'第 {page + 1} 页获取失败，停止')
                break
            items = parse_reviews(data)
            all_items.extend(items)
            print(f'第 {page + 1} 页已获取 {len(items)} 条评论')

            # 没有 next 字段说明没有更多了
            if "next" not in data:
                print('没有更多评论，提前结束')
                break

        #写入csv
        path = f'{review_path}/{cur_id}.csv'
        fieldnames = ["id", "title", "userName", "review", "rating", "date", "isEdited"]
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_items)
        print(f'完成 {cur_id}，共 {len(all_items)} 条评论写入 {path}\n')

if __name__ == '__main__':
    main()