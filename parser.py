import requests
import json
import time
import argparse
import sys
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import os
import urllib3

# Отключаем предупреждения о небезопасном SSL (для проверки старых сайтов)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === КОНФИГУРАЦИЯ ===
API_KEY = "ВАШ_2GIS_КЛЮЧ"
CATEGORIES = ["барбершоп", "салон красоты", "парикмахерская", "косметология"]
CHECKPOINT_INTERVAL = 10
THREADS = 10
TIMEOUT = 5

class BusinessParser:
    def __init__(self, city_name, max_count, output_file):
        self.city_name = city_name
        self.max_count = max_count
        self.output_file = output_file
        self.city_id = None
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_city_id(self):
        print(f"[*] Определение ID города для: {self.city_name}...")
        url = "https://catalog.api.2gis.ru/3.0/items/geocode"
        params = {
            "q": self.city_name,
            "fields": "items.point",
            "key": API_KEY
        }
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if "result" in data and "items" in data["result"]:
                for item in data["result"]["items"]:
                    # Ищем именно город или населенный пункт
                    if item.get("subtype") in ["city", "town", "settlement"] or item.get("type") == "adm_div":
                        self.city_id = item["id"]
                        print(f"[+] Город найден. ID: {self.city_id}")
                        return True
            print(f"[-] Город '{self.city_name}' не найден.")
            return False
        except Exception as e:
            print(f"[-] Ошибка геокодера: {e}")
            return False

    def search_businesses(self):
        all_items = []
        for query in CATEGORIES:
            if len(all_items) >= self.max_count:
                break

            print(f"[*] Поиск по категории: {query}...")
            page = 1
            while len(all_items) < self.max_count:
                url = "https://catalog.api.2gis.ru/3.0/items"
                params = {
                    "q": query,
                    "city_id": self.city_id,
                "fields": "items.point,items.contacts,items.reviews,items.rating,items.address_name,items.address_comment",
                    "page": page,
                    "page_size": 50,
                    "key": API_KEY
                }
                try:
                    resp = self.session.get(url, params=params, timeout=10)
                    data = resp.json()

                    if "result" not in data or "items" not in data["result"]:
                        break

                    items = data["result"]["items"]
                    if not items:
                        break

                    for item in items:
                        if len(all_items) >= self.max_count:
                            break

                        # Извлекаем контакты
                        contacts = item.get("contacts", {})
                        phone = ""
                        website = ""

                        # Телефон
                        if "contacts" in item:
                            # В 2GIS контакты могут быть списком в ключе 'contacts' или вложенными
                            # Обычно это структура типа {"contacts": [{"type": "phone", "value": "..."}]}
                            for c in item.get("contacts", {}).get("list", []):
                                if c["type"] == "phone":
                                    phone = c["value"]
                                    break

                            # Поиск сайта
                            for c in item.get("contacts", {}).get("list", []):
                                if c["type"] == "website":
                                    website = c["value"]
                                    break

                        address = item.get("address_name", "")
                        if not address:
                            address = item.get("address_comment", "N/A")

                        business = {
                            "name": item.get("name", "N/A"),
                            "phone": phone,
                            "website": website,
                            "rating": item.get("rating", 0),
                            "reviews": item.get("reviews", {}).get("general_count", 0),
                            "address": address,
                            "status": "ОПРЕДЕЛЯЕТСЯ"
                        }

                        if not website:
                            business["status"] = "НУЖЕН САЙТ"

                        all_items.append(business)

                        if len(all_items) % CHECKPOINT_INTERVAL == 0:
                            self.save_checkpoint(all_items)

                    page += 1
                    time.sleep(0.5) # Небольшая пауза между страницами
                except Exception as e:
                    print(f"[-] Ошибка поиска: {e}")
                    break

        self.results = all_items
        print(f"[+] Всего собрано: {len(self.results)} контактов.")

    def check_site_status(self, business):
        if business["status"] == "НУЖЕН САЙТ":
            return business

        url = business["website"]
        if not url.startswith("http"):
            url = "http://" + url

        try:
            resp = self.session.get(url, timeout=TIMEOUT, verify=False)
            if resp.status_code != 200:
                business["status"] = "НЕ ДОСТУПЕН"
                return business

            html = resp.text.lower()
            soup = BeautifulSoup(html, "lxml")

            # 1. Признаки "НОРМ" (Тильда, Редимаг, ВК, ТГ, Вордпресс)
            norm_markers = ["tilda", "readymag", "tg://", "t.me/", "vk.com/app", "wp-content", "wp-"]
            is_modern_tags = soup.find_all(["nav", "main", "section"])

            has_viewport = soup.find("meta", attrs={"name": "viewport"})

            if any(marker in html for marker in norm_markers) or is_modern_tags:
                business["status"] = "НОРМ"
                return business

            # 2. Проверка на "УСТАРЕЛ"
            # Если нет вьюпорта ИЛИ есть табличная верстка ИЛИ нет классов
            has_table_layout = soup.find("table", attrs={"width": True}) or soup.find("table", attrs={"cellpadding": True})
            has_flex_grid = ".flex" in html or ".grid" in html or "display:flex" in html or "display:grid" in html

            # Если нет адаптива или древние признаки
            if not has_viewport or has_table_layout or not has_flex_grid:
                business["status"] = "УСТАРЕЛ"
            else:
                business["status"] = "НОРМ"

        except Exception:
            business["status"] = "НЕ ДОСТУПЕН"

        return business

    def process_sites(self):
        print(f"[*] Анализ сайтов в {THREADS} потоков...")
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            self.results = list(executor.map(self.check_site_status, self.results))

    def save_checkpoint(self, items):
        # Временное сохранение в JSON для безопасности
        with open("checkpoint.json", "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=4)

    def generate_html(self):
        print(f"[*] Генерация финального отчета: {self.output_file}...")

        # Фильтрация
        filtered_results = [r for r in self.results if r["status"] in ["НУЖЕН САЙТ", "УСТАРЕЛ", "НЕ ДОСТУПЕН"]]

        # Сортировка по рейтингу (высокие сверху)
        # Если рейтинга нет, считаем его 0.0
        def get_rating(x):
            try:
                return float(x.get("rating") or 0)
            except (ValueError, TypeError):
                return 0.0

        filtered_results.sort(key=get_rating, reverse=True)

        html_template = """
        <html>
        <head>
            <meta charset="utf-8">
            <title>Потенциальные клиенты - {city}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; padding: 30px; color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                h2 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ text-align: left; padding: 14px 18px; border-bottom: 1px solid #eee; }}
                th {{ background-color: #f8f9fa; color: #5f6368; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; }}
                tr:hover {{ background-color: #f1f8ff; }}
                .status-need {{ background: #fdecea; color: #d93025; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; font-weight: bold; }}
                .status-old {{ background: #fff4e5; color: #e27200; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; font-weight: bold; }}
                .status-dead {{ background: #f1f3f4; color: #5f6368; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; font-weight: bold; }}
                .rating {{ color: #f4b400; font-weight: bold; }}
                a {{ color: #1a73e8; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .stats {{ margin-bottom: 20px; font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
            <h2>🎯 Потенциальные клиенты: {city}</h2>
            <div class="stats">Найдено контактов: {total_leads} | Дата сбора: {date}</div>
            <table>
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Телефон</th>
                        <th>Сайт</th>
                        <th>Рейтинг</th>
                        <th>Отзывы</th>
                        <th>Адрес</th>
                        <th>Статус сайта</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </body>
        </html>
        """

        rows = ""
        for r in filtered_results:
            status_class = ""
            if r["status"] == "НУЖЕН САЙТ": status_class = "status-need"
            elif r["status"] == "УСТАРЕЛ": status_class = "status-old"
            elif r["status"] == "НЕ ДОСТУПЕН": status_class = "status-dead"

            site_link = f'<a href="{r["website"]}" target="_blank">{r["website"]}</a>' if r["website"] else "-"

            rows += f"""
            <tr>
                <td><b>{r['name']}</b></td>
                <td><code>{r['phone']}</code></td>
                <td>{site_link}</td>
                <td class="rating">{r['rating']} ★</td>
                <td>{r['reviews']}</td>
                <td><small>{r['address']}</small></td>
                <td><span class="{status_class}">{r['status']}</span></td>
            </tr>
            """

        final_html = html_template.format(
            city=self.city_name,
            rows=rows,
            total_leads=len(filtered_results),
            date=time.strftime("%d.%m.%Y %H:%M")
        )

        with open(self.output_file, "w", encoding="utf-8-sig") as f:
            f.write(final_html)

        print(f"[+] Готово! Результаты сохранены в {self.output_file}")
        print(f"[+] Найдено подходящих лидов: {len(filtered_results)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Парсер бизнесов которым нужен сайт")
    parser.add_argument("city", help="Название города (например, Москва)")
    parser.add_argument("--max", type=int, default=500, help="Максимальное количество контактов для сбора")
    parser.add_argument("--output", default="result.html", help="Имя выходного файла")

    args = parser.parse_args()

    if API_KEY == "ВАШ_2GIS_КЛЮЧ":
        print("[-] ОШИБКА: Пожалуйста, вставьте ваш 2GIS API ключ в переменную API_KEY внутри скрипта.")
        sys.exit(1)

    p = BusinessParser(args.city, args.max, args.output)
    if p.get_city_id():
        p.search_businesses()
        if p.results:
            p.process_sites()
            p.generate_html()
        else:
            print("[-] Результаты не найдены.")
