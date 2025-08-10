import json
import os

# Загружаем переводы один раз при старте
translations = {}
for lang in ['ru', 'en']:
    path = os.path.join('locales', f'{lang}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            translations[lang] = json.load(f)

def get_text(key: str, lang: str, **kwargs) -> str:
    """Получает текст по ключу для нужного языка и форматирует его."""
    text_template = translations.get(lang, translations['en']).get(key, f"_{key}_")
    return text_template.format(**kwargs)