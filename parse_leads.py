import csv
import re

def parse_leads(file_path):
    with open(file_path, 'rb') as f:
        content_bytes = f.read()

    try:
        content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        content = content_bytes.decode('latin-1', errors='ignore')

    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Split by position:N
    parts = re.split(r'\nposition:\d+\n?', content)

    leads = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part: continue

        lines = part.split('\n')
        lead = {}

        first_line = lines[0].strip()
        if first_line.startswith('title:'):
            lead['title'] = first_line.split(':', 1)[1].strip()
        else:
            lead['title'] = first_line

        active_multi = None
        for line in lines[1:]:
            line = line.strip()
            if not line: continue

            if line in ['types', 'openingHours', 'bookingLinks']:
                active_multi = line
                lead[active_multi] = []
                continue

            if ':' in line:
                parts_line = line.split(':', 1)
                key = parts_line[0].strip()
                val = parts_line[1].strip()

                if active_multi == 'openingHours' and any(day in key for day in ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье', 'четверг', 'закрыто']):
                     lead['openingHours'].append(f"{key}: {val}")
                elif active_multi and key.isdigit():
                     lead[active_multi].append(val)
                else:
                    lead[key] = val
                    active_multi = None
            else:
                if not lead.get('title'):
                    lead['title'] = line

        if lead.get('title') or lead.get('address'):
            leads.append(lead)

    return leads

def format_leads(leads):
    formatted = []
    # Expanded city list based on address analysis
    cities = [
        'Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань',
        'Нижний Новгород', 'Челябинск', 'Ростов-на-Дону', 'Самара', 'Омск',
        'Уфа', 'Красноярск', 'Пермь', 'Воронеж', 'Волгоград', 'Краснодар'
    ]

    for lead in leads:
        title = lead.get('title', '').strip()
        if not title or title.lower() in ['types', 'openinghours', 'bookinglinks', 'engine', 'google', 'maps', 'hl', 'gl']:
            if lead.get('address'):
                title = lead.get('address').split(',')[0]
            else:
                continue

        types_list = lead.get('types', [])
        types_str = ", ".join(types_list)
        if not types_str:
            types_str = lead.get('type', '')

        hours_list = lead.get('openingHours', [])
        hours_str = " | ".join(hours_list)

        links_list = lead.get('bookingLinks', [])
        links_str = " ".join(links_list)

        q = lead.get('q', '')
        addr = lead.get('address', '')

        # Improved city extraction: check address first, then query
        city = ""
        # Look for city name in address components
        addr_parts = [p.strip() for p in addr.split(',')]
        found = False
        for c in cities:
            if any(c in p for p in addr_parts):
                city = c
                found = True
                break

        if not found:
            for c in cities:
                if c in q:
                    city = c
                    break

        formatted.append({
            'Название': title,
            'Телефон': lead.get('phoneNumber', ''),
            'Сайт': lead.get('website', ''),
            'Адрес': addr,
            'Город': city,
            'Рейтинг': lead.get('rating', ''),
            'Кол-во отзывов': lead.get('ratingCount', ''),
            'Категории': types_str,
            'Часы работы': hours_str,
            'Ссылки для записи': links_str,
            'Запрос': q
        })
    return formatted

if __name__ == "__main__":
    leads_data = parse_leads('лиды.txt')
    formatted = format_leads(leads_data)

    if formatted:
        keys = formatted[0].keys()
        with open('leads_structured.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(formatted)
        print(f"Success: {len(formatted)} leads saved.")
    else:
        print("Failed: No leads found.")
