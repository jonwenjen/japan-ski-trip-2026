import os
import json
from google import genai
from github import Github

def run_spark_updater():
    gh_token = os.environ.get("GH_PAT")
    repo_name = os.environ.get("GH_REPO")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    user_instruction = os.environ.get("SPARK_INSTRUCTION", "進行常規資料校驗與格式標準化")

    if not gh_token or not repo_name or not gemini_key:
        raise ValueError("請確認已設定 GH_PAT, GH_REPO 與 GEMINI_API_KEY 環境變數。")

    # 1. 抓取目前 GitHub 上的 itinerary.json
    gh = Github(gh_token)
    repo = gh.get_repo(repo_name)
    file_content = repo.get_contents("itinerary.json", ref="main")
    current_json = json.loads(file_content.decoded_content.decode("utf-8"))

    # 2. 呼叫 Gemini 進行自然語言推理與更新
    client = genai.Client(api_key=gemini_key)
    prompt = f"""
    你是一名專業的日本滑雪旅行社專員與資料工程師。請根據調整需求，更新現有的 itinerary.json。

    【目前 JSON 資料】：
    {json.dumps(current_json, ensure_ascii=False)}

    【動態調整需求】：
    {user_instruction}

    【輸出規範】：
    1. 僅輸出純合法的 JSON 字串，嚴禁輸出 Markdown 標記（如 ```json）。
    2. 維持所有既有欄位架構（trip_title, flights, days 陣列）。
    3. 新增地點必須包含標準可點擊的 Google Maps 搜尋 URL：
       [https://www.google.com/maps/search/?api=1&query=名稱](https://www.google.com/maps/search/?api=1&query=名稱)
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    clean_json_str = response.text.strip().replace("```json", "").replace("```", "").strip()

    # 3. 自動 Commit 並 Push 回 GitHub main 分支
    repo.update_file(
        path="itinerary.json",
        message=f"Gemini Spark 動態更新: {user_instruction[:30]}",
        content=clean_json_str,
        sha=file_content.sha,
        branch="main"
    )
    print("itinerary.json 已成功提交並同步至 GitHub。")

if __name__ == "__main__":
    run_spark_updater()
