# Прогноз погоды с визуализацией (Streamlit)

Веб‑приложение на Streamlit для просмотра текущей погоды и прогноза (5 дней / 3 часа) с графиками на Plotly. Источник данных — OpenWeather.

## Возможности
- Ввод города, выбор единиц (метрика/империал) и языка (ru/en)
- Текущая погода: температура, ощущается, влажность, ветер, иконка
- Прогноз: графики температуры, влажности, скорости ветра; таблица
- Кэширование запросов

## Установка
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## API ключ OpenWeather
Получите ключ на `https://home.openweathermap.org/api_keys`.

Способы задать ключ:
- Через переменную окружения `OPENWEATHER_API_KEY`
- Через Streamlit Secrets: создайте файл `.streamlit/secrets.toml`:

```toml
OPENWEATHER_API_KEY = "ВАШ_API_КЛЮЧ"
```

- Либо в интерфейсе приложения в боковой панели ввести ключ вручную

Пример файла в репозитории: `.streamlit/secrets.example.toml`.

## Запуск
```bash
streamlit run streamlit_app.py
```

Откройте указанный адрес в браузере (обычно `http://localhost:8501`).

## Стек
- Streamlit
- OpenWeather API (`/weather`, `/forecast`)
- Plotly (визуализация)
- Pandas



