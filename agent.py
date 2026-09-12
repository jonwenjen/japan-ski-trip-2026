import os
import json
import base64
from google import genai
from github import Github, Auth

# 完整的 index.html 前端樣板 (包含 Tailwind CSS、折疊手風琴與地圖展示)
COMPLETE_INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>2026 日本滑雪・志賀高原極上粉雪行</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    details > summary { list-style: none; cursor: pointer; user-select: none; }
    details > summary::-webkit-details-marker { display: none; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen">
  <header class="bg-gradient-to-r from-blue-950 via-slate-900 to-indigo-950 border-b border-slate-800 py-8 px-4 text-center">
    <div class="max-w-4xl mx-auto">
      <span class="inline-block bg-blue-500/20 text-blue-300 text-xs font-semibold px-3 py-1 rounded-full border border-blue-500/30 mb-2">
        <i class="fa-solid fa-snowflake mr-1"></i> 日本滑雪技術團隊 ＆ 旅遊顧問規劃
      </span>
      <h1 id="trip-title" class="text-2xl md:text-4xl font-extrabold text-white mb-2">載入行程中...</h1>
      <p id="flight-info" class="text-slate-400 text-xs md:text-sm"></p>
    </div>
  </header>

  <main class="max-w-4xl mx-auto px-4 py-8 space-y-6" id="itinerary-container"></main>

  <footer class="text-center py-6 text-slate-500 text-xs border-t border-slate-900">
    <p>Powered by Gemini Spark Travel Automation & GitHub Pages</p>
  </footer>

  <script>
    fetch("itinerary.json?t=" + Date.now())
      .then(function(res) {
        if (!res.ok) { throw new Error("HTTP " + res.status); }
        return res.json();
      })
      .then(function(data) {
        document.getElementById("trip-title").innerText = data.trip_title || "2026 日本滑雪行程";
        if (data.flights) {
          document.getElementById("flight-info").innerHTML = 
            '<i class="fa-solid fa-plane-arrival text-emerald-400 mr-1"></i>去程：' + (data.flights.arrival || "") + 
            ' &nbsp;|&nbsp; <i class="fa-solid fa-plane-departure text-rose-400 mr-1"></i>回程：' + (data.flights.departure || "");
        }

        var container = document.getElementById("itinerary-container");
        container.innerHTML = "";

        data.days.forEach(function(day) {
          var card = document.createElement("div");
          card.className = "bg-slate-900/90 rounded-2xl border border-slate-800 p-5 md:p-6 shadow-xl space-y-4";

          var skiHtml = "";
          if (day.ski_resort) {
            skiHtml = '<div class="bg-slate-950/80 p-4 rounded-xl border border-sky-500/30">' +
              '<div class="flex items-center justify-between mb-2">' +
                '<h4 class="text-sky-400 font-bold text-sm md:text-base flex items-center gap-2">' +
                  '<i class="fa-solid fa-person-skiing"></i> ' + day.ski_resort.name +
                '</h4>' +
                '<a href="' + day.ski_resort.official_link + '" target="_blank" rel="noopener noreferrer" class="text-xs bg-sky-600 hover:bg-sky-500 text-white px-2.5 py-1 rounded transition">' +
                  '官網全景圖 <i class="fa-solid fa-arrow-up-right-from-square ml-1 text-[10px]"></i>' +
                '</a>' +
              '</div>' +
              '<p class="text-xs text-slate-300 mb-3">' + (day.ski_resort.features || "") + '</p>' +
              '<div class="rounded-lg overflow-hidden border border-slate-700">' +
                '<img src="' + day.ski_resort.map_img + '" alt="' + day.ski_resort.name + ' 雪道圖" class="w-full h-auto object-cover hover:scale-105 transition duration-300">' +
              '</div>' +
            '</div>';
          }

          var friendHtml = "";
          if (day.friend_transit) {
            friendHtml = '<div class="bg-amber-950/30 border border-amber-500/30 p-3.5 rounded-xl text-xs text-amber-200">' +
              '<div class="font-bold flex items-center gap-2 mb-1 text-amber-400">' +
                '<i class="fa-solid fa-user-clock"></i> ' + (day.friend_transit.title || "友人交通接駁") +
              '</div>' +
              '<p>' + day.friend_transit.details + '</p>' +
            '</div>';
          }

          var attractionsHtml = "";
          if (day.attractions && day.attractions.length > 0) {
            var attItems = day.attractions.map(function(a) {
              return '<li>・<a href="' + a.map + '" target="_blank" rel="noopener noreferrer" class="text-slate-200 hover:text-indigo-300 underline underline-offset-2">' + a.name + ' <i class="fa-solid fa-location-dot text-rose-500 ml-1 text-[10px]"></i></a></li>';
            }).join("");
            attractionsHtml = '<div class="bg-slate-950/50 p-3 rounded-xl border border-slate-800 text-xs">' +
              '<span class="font-bold text-indigo-400 block mb-1.5"><i class="fa-solid fa-compass mr-1"></i> 市區推薦景點：</span>' +
              '<ul class="space-y-1">' + attItems + '</ul>' +
            '</div>';
          }

          var recHtml = "";
          if (day.recommendations) {
            var buildList = function(items, hoverColor) {
              if (!items || !items.length) { return '<li class="text-slate-500">暫無推薦項目</li>'; }
              return items.map(function(item) {
                return '<li>・<a href="' + item.map + '" target="_blank" rel="noopener noreferrer" class="text-slate-200 hover:text-' + hoverColor + '-300 underline underline-offset-2">' + item.name + ' <i class="fa-solid fa-arrow-up-right-from-square text-[10px] ml-1"></i></a></li>';
              }).join("");
            };

            var restaurantList = day.recommendations.restaurant || [];
            var dessertList = day.recommendations.dessert_pastry || day.recommendations.dessert_drink || [];
            var beverageList = day.recommendations.beverage || [];
            var souvenirList = day.recommendations.souvenir || [];

            recHtml = '<details class="group bg-slate-950/60 rounded-xl border border-slate-800 p-3.5 transition">' +
              '<summary class="flex justify-between items-center text-xs md:text-sm font-semibold text-slate-300 hover:text-white">' +
                '<span class="flex items-center gap-2">' +
                  '<i class="fa-solid fa-utensils text-emerald-400"></i>' +
                  '<span>點選查看在地推薦：私房餐廳・甜點糕點・飲品・伴手禮</span>' +
                '</span>' +
                '<span class="text-slate-500 group-open:rotate-180 transition-transform duration-200">' +
                  '<i class="fa-solid fa-chevron-down"></i>' +
                '</span>' +
              '</summary>' +
              '<div class="pt-4 border-t border-slate-800 mt-3 space-y-3.5 text-xs">' +
                '<div>' +
                  '<span class="font-bold text-emerald-400 block mb-1">【正餐餐廳】</span>' +
                  '<ul class="space-y-1">' + buildList(restaurantList, "emerald") + '</ul>' +
                '</div>' +
                '<div>' +
                  '<span class="font-bold text-amber-400 block mb-1">【甜點・特色糕點】</span>' +
                  '<ul class="space-y-1">' + buildList(dessertList, "amber") + '</ul>' +
                '</div>' +
                '<div>' +
                  '<span class="font-bold text-cyan-400 block mb-1">【特色飲品・地酒】</span>' +
                  '<ul class="space-y-1">' + buildList(beverageList, "cyan") + '</ul>' +
                '</div>' +
                '<div>' +
                  '<span class="font-bold text-fuchsia-400 block mb-1">【必買伴手禮】</span>' +
                  '<ul class="space-y-1">' + buildList(souvenirList, "fuchsia") + '</ul>' +
                '</div>' +
              '</div>' +
            '</details>';
          }

          var stayContent = day.stay;
          if (day.stay_map) {
            stayContent = '<a href="' + day.stay_map + '" target="_blank" rel="noopener noreferrer" class="text-slate-200 hover:text-indigo-300 underline underline-offset-2">' + day.stay + ' <i class="fa-solid fa-location-dot text-rose-400 text-[10px] ml-0.5"></i></a>';
          }

          card.innerHTML = 
            '<div class="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-800 pb-3">' +
              '<span class="text-xl md:text-2xl font-black text-sky-400 font-mono">' + day.date + '</span>' +
              '<span class="text-sm md:text-base font-bold text-slate-200">' + day.day_title + '</span>' +
            '</div>' +
            '<div class="space-y-2 text-xs md:text-sm text-slate-300">' +
              '<div class="flex items-start gap-2">' +
                '<i class="fa-solid fa-hotel text-indigo-400 mt-0.5"></i>' +
                '<div><span class="text-slate-400">住宿：</span>' + stayContent + '</div>' +
              '</div>' +
              '<div class="flex items-start gap-2">' +
                '<i class="fa-solid fa-train-subway text-emerald-400 mt-0.5"></i>' +
                '<div><span class="text-slate-400">交通規劃：</span>' + day.transit + '</div>' +
              '</div>' +
            '</div>' +
            friendHtml +
            attractionsHtml +
            skiHtml +
            recHtml;

          container.appendChild(card);
        });
      })
      .catch(function(err) {
        console.error("載入失敗:", err);
        document.getElementById("trip-title").innerText = "無法載入行程資料，請確認 itinerary.json 是否存在。";
      });
  </script>
</body>
</html>"""

def sync_index_html(repo):
    """自動確保 GitHub 上的 index.html 100% 完整無缺"""
    try:
        file_content = repo.get_contents("index.html", ref="main")
        current_html = file_content.decoded_content.decode("utf-8")
        if current_html.strip() != COMPLETE_INDEX_HTML.strip():
            repo.update_file(
                path="index.html",
                message="Gemini Spark: 自動同步並修復完整 index.html 前端",
                content=COMPLETE_INDEX_HTML,
                sha=file_content.sha,
                branch="main"
            )
            print("index.html 已自動修復並成功提交至 GitHub！")
        else:
            print("index.html 結構已是最新完整版。")
    except Exception:
        repo.create_file(
            path="index.html",
            message="Gemini Spark: 自動建立完整 index.html 前端",
            content=COMPLETE_INDEX_HTML,
            branch="main"
        )
        print("index.html 已自動建立成功！")

def run_spark_updater():
    gh_token = os.environ.get("GH_PAT", "").strip()
    repo_name = os.environ.get("GH_REPO", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    user_instruction = os.environ.get("SPARK_INSTRUCTION", "進行常規資料校驗與格式標準化").strip()

    if not gh_token or not repo_name or not gemini_key:
        raise ValueError("缺少必要的環境變數：GH_PAT, GH_REPO 或 GEMINI_API_KEY。")

    auth = Auth.Token(gh_token)
    gh = Github(auth=auth)
    repo = gh.get_repo(repo_name)

    # 1. 自動檢測並修復 GitHub 上的 index.html (免手動複製)
    sync_index_html(repo)

    # 2. 抓取並透過 Gemini 3.6 Flash 動態調整 itinerary.json
    file_content = repo.get_contents("itinerary.json", ref="main")
    current_json = json.loads(file_content.decoded_content.decode("utf-8"))

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
        model="gemini-3.6-flash",
        contents=prompt
    )

    clean_json_str = response.text.strip().replace("```json", "").replace("```", "").strip()

    repo.update_file(
        path="itinerary.json",
        message="Gemini Spark 自動更新: " + user_instruction[:30],
        content=clean_json_str,
        sha=file_content.sha,
        branch="main"
    )
    print("itinerary.json 已成功同步更新至 GitHub。")

if __name__ == "__main__":
    run_spark_updater()
