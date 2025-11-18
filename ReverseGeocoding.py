import requests
from playwright.sync_api import sync_playwright
import json
import os


def get_address_from_coordinates(lat, lon):
    headers = {'accept': '*/*', 'accept-language': 'zh-CN,zh;q=0.9',
               'referer': 'https://developer.amap.com/demo/javascript-api/example/geocoder/regeocoding',
               'user-agent': 'Mozilla/5.0'}
    loc = f"{lon},{lat}"
    url_tpl = 'https://developer.amap.com/AMapService/v3/geocode/regeo?key={key}&s=rsv3&language=zh_cn&location={loc}&radius=1000&callback=jsonp_765657_&platform=JS&logversion=2.0&appname=https%3A%2F%2Fdeveloper.amap.com%2Fdemo%2Fjavascript-api%2Fexample%2Fgeocoder%2Fregeocoding&csid=123456&sdkversion=1.4.27'

    def get_cookies_key():
        if os.path.exists("cookies.json"):
            try:
                with open("cookies.json", "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if saved.get("cookies") and saved.get("key"):
                        return saved["cookies"], saved["key"]
            except Exception as e:
                print(f"读取cookies失败: {e}")

        target_keys = ['cna', 'passport_login', 'xlly_s', 'HMACCOUNT', 'Hm_lvt_c8ac07c199b1c09a848aaab761f9f909',
                       'Hm_lpvt_c8ac07c199b1c09a848aaab761f9f909', 'tfstk']
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context().new_page()
            page.goto("https://developer.amap.com/demo/javascript-api/example/geocoder/regeocoding")
            page.wait_for_timeout(3000)
            cookies = {c['name']: c['value'] for c in page.context.cookies() if c['name'] in target_keys}
            key = page.get_attribute("#code_origin", "data-jskey")
            browser.close()

        with open("cookies.json", "w", encoding="utf-8") as f:
            json.dump({"cookies": cookies, "key": key}, f, ensure_ascii=False)
        return cookies, key

    def get_address(cookies, key):
        if not cookies or not key:
            return None
        try:
            url = url_tpl.format(key=key, loc=loc)
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
            if resp.status_code == 200 and "formatted_address" in resp.text:
                json_str = resp.text[resp.text.index('(') + 1:resp.text.rindex(')')]
                return json.loads(json_str).get("regeocode", {}).get("formatted_address", "")
        except Exception as e:
            print(f"请求失败: {e}")
        return None

    cookies, key = get_cookies_key()
    addr = get_address(cookies, key)
    if not addr:
        cookies, key = get_cookies_key()
        addr = get_address(cookies, key)

    return addr or "获取失败"


if __name__ == "__main__":
    print(f"坐标 (39.9087, 116.3975) 对应的地址是：{get_address_from_coordinates(39.9087, 116.3975)}")
