import os
import json
from google import genai
from github import Github, Auth

def run_spark_updater():
    # 透過 .strip() 自動清除意外複製到的換行符號 (\n) 與空格
    gh_token = os.environ.get("GH_PAT", "").strip()
    repo_name = os.environ.get("GH_REPO", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    user_instruction = os.environ.get("SPARK_INSTRUCTION", "進行常規資料校驗與格式標準化").strip()

    if not gh_token or not repo_name or not gemini_key:
        raise ValueError("缺少必要的環境變數：GH_PAT, GH_REPO 或 GEMINI_API_KEY。")

    # 1. 使用現代 Auth 語法連接 GitHub（消除 DeprecationWarning）
    auth = Auth.Token(gh_token)
    gh = Github(auth=auth)
    repo = gh.get_repo(repo_name)
    file_content = repo.get_contents("itinerary.json", ref="main")
    current_json = json.loads(file_content.decoded_content.decode("utf-8"))

    # 2. 呼叫 Gemini 進行推理與動態更新
    client = genai.Client(api_key=gemini_key)
    prompt = (
        "你是一名專業的日本滑雪旅行社專員與資料工程師。請根據調整需求，更新現有的 itinerary.json。\n\n"
        "【目前 JSON 資料】：\n" + json.dumps(current_json, ensure_ascii=False) + "\n\n"
        "【動態調整需求】：\n" + user_instruction + "\n\n"
        "【輸出規範】：\n"
        "1. 僅輸出合法的純 JSON 字串，嚴禁輸出 Markdown 標記（如 ```json）。\n"
        "2. 維持所有既有欄位架構（trip_title, flights, days 陣列）。\n"
        "3. 新增地點必須附帶標準 Google Maps 搜尋 URL：[https://www.google.com/maps/search/?api=1&query=名稱](https://www.google.com/maps/search/?api=1&query=名稱)\n"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    clean_json_str = response.text.strip().replace("```json", "").replace("```", "").strip()

    # 3. 自動 Commit 並 Push 回 main 分支
    repo.update_file(
        path="itinerary.json",
        message="Gemini Spark 自動更新: " + user_instruction[:30],
        content=clean_json_str,
        sha=file_content.sha,
        branch="main"
    )
    print("itinerary.json 已成功提交並同步至 GitHub。")

if __name__ == "__main__":
    run_spark_updater()
