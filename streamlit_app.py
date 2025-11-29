import os
from datetime import datetime
from typing import Dict, Optional, Tuple
import pandas as pd
import requests
import streamlit as st
import plotly.express as px

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

@st.cache_data(show_spinner=False)
def fetch_current_weather(city: str, api_key: str, units: str, lang: str) -> Tuple[Optional[Dict], Optional[str]]:
    params = {"q": city, "appid": api_key, "units": units, "lang": lang}
    try:
        response = requests.get(f"{OPENWEATHER_BASE_URL}/weather", params=params, timeout=15)
        if response.status_code == 200:
            return response.json(), None
        try:
            err_json = response.json()
            message = err_json.get("message") or str(err_json)
        except Exception:
            message = response.text
        return None, f"HTTP {response.status_code}: {message}"
    except requests.RequestException as exc:
        return None, f"Network error: {exc}"


@st.cache_data(show_spinner=False)
def fetch_forecast(city: str, api_key: str, units: str, lang: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    params = {"q": city, "appid": api_key, "units": units, "lang": lang}
    try:
        response = requests.get(f"{OPENWEATHER_BASE_URL}/forecast", params=params, timeout=15)
        if response.status_code != 200:
            try:
                err_json = response.json()
                message = err_json.get("message") or str(err_json)
            except Exception:
                message = response.text
            return None, f"HTTP {response.status_code}: {message}"
        data = response.json()
        list_items = data.get("list", [])
        if not list_items:
            return None, "Empty forecast list from API"

        df = pd.DataFrame(list_items)
        main_df = pd.json_normalize(df["main"]).add_prefix("main.")
        wind_df = pd.json_normalize(df["wind"]).add_prefix("wind.")
        weather_main = df["weather"].apply(lambda x: x[0] if isinstance(x, list) and x else {})
        weather_df = pd.json_normalize(weather_main).add_prefix("weather.")
        clouds_df = pd.json_normalize(df.get("clouds", {})).add_prefix("clouds.")

        result = pd.concat(
            [
                pd.to_datetime(df["dt"], unit="s").rename("dt"),
                df["dt_txt"].rename("dt_txt"),
                main_df,
                wind_df,
                weather_df,
                clouds_df,
            ],
            axis=1,
        )
        for col, default in [
            ("main.temp", None),
            ("main.feels_like", None),
            ("main.humidity", None),
            ("wind.speed", None),
            ("weather.description", ""),
        ]:
            if col not in result.columns:
                result[col] = default

        return result, None
    except requests.RequestException as exc:
        return None, f"Network error: {exc}"

def get_api_key_from_env_or_ui() -> Tuple[Optional[str], bool]:
    api_key = None
    from_secrets = False

    try:
        api_key = st.secrets.get("OPENWEATHER_API_KEY") 
        if api_key:
            from_secrets = True
    except Exception:
        api_key = None

    if not api_key:
        api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        api_key = st.sidebar.text_input("API ключ OpenWeather", type="password", help="Получите на openweathermap.org -> API keys")

    return api_key, from_secrets


def format_location_block(current: Dict) -> str:
    name = current.get("name")
    sys_info = current.get("sys", {})
    country = sys_info.get("country", "")
    return f"{name}, {country}" if name else "—"


def main() -> None:
    st.set_page_config(page_title="Прогноз погоды", page_icon="☀️", layout="wide")
    st.title("Прогноз погоды с визуализацией")

    with st.sidebar:
        st.header("Настройки")
        default_city = "Almaty"
        city = st.text_input("Город", value=default_city)
        units_label = st.radio("Единицы измерения", options=["metric", "imperial"], format_func=lambda x: "Метрика (°C, м/с)" if x == "metric" else "Империал (°F, mph)")
        lang = st.selectbox("Язык", options=["ru", "en"], index=0)
        api_key, from_secrets = get_api_key_from_env_or_ui()

    if not api_key:
        st.warning("Укажите API ключ OpenWeather в боковой панели или через secrets.")
        st.stop()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Текущая погода")
        current, current_err = fetch_current_weather(city, api_key, units_label, lang)
        if not current:
            st.error("Не удалось получить текущую погоду. Проверьте название города и ключ API.")
            if current_err:
                st.code(current_err)
        else:
            location_str = format_location_block(current)
            weather = (current.get("weather") or [{}])[0]
            main = current.get("main", {})
            wind = current.get("wind", {})
            icon = weather.get("icon")
            description = weather.get("description", "—")
            temp = main.get("temp")
            feels = main.get("feels_like")
            humidity = main.get("humidity")
            wind_speed = wind.get("speed")

            units_temp = "°C" if units_label == "metric" else "°F"
            units_wind = "м/с" if units_label == "metric" else "mph"

            st.metric(label=f"{location_str}", value=f"{temp} {units_temp}" if temp is not None else "—", delta=f"Ощущается как {feels} {units_temp}" if feels is not None else None)
            cols = st.columns(2)
            with cols[0]:
                st.write(f"Влажность: {humidity}%" if humidity is not None else "Влажность: —")
                st.write(f"Ветер: {wind_speed} {units_wind}" if wind_speed is not None else "Ветер: —")
            with cols[1]:
                if icon:
                    st.image(f"https://openweathermap.org/img/wn/{icon}@2x.png", width=90)
                st.caption(description.capitalize())

    with col2:
        st.subheader("Прогноз (5 дней / 3 часа)")
        forecast_df, forecast_err = fetch_forecast(city, api_key, units_label, lang)
        if forecast_df is None or forecast_df.empty:
            st.error("Не удалось получить прогноз. Проверьте название города и ключ API.")
            if forecast_err:
                st.code(forecast_err)
        else:
            units_temp = "°C" if units_label == "metric" else "°F"
            fig_temp = px.line(
                forecast_df,
                x="dt",
                y="main.temp",
                title=f"Температура по времени ({units_temp})",
                markers=True,
                labels={"dt": "Время", "main.temp": f"Температура, {units_temp}"},
            )
            fig_temp.update_traces(mode="lines+markers")
            st.plotly_chart(fig_temp, use_container_width=True)

            fig_hum = px.line(
                forecast_df,
                x="dt",
                y="main.humidity",
                title="Влажность по времени (%)",
                markers=True,
                labels={"dt": "Время", "main.humidity": "Влажность, %"},
            )
            st.plotly_chart(fig_hum, use_container_width=True)

            wind_units = "м/с" if units_label == "metric" else "mph"
            fig_wind = px.line(
                forecast_df,
                x="dt",
                y="wind.speed",
                title=f"Скорость ветра по времени ({wind_units})",
                markers=True,
                labels={"dt": "Время", "wind.speed": f"Ветер, {wind_units}"},
            )
            st.plotly_chart(fig_wind, use_container_width=True)

            with st.expander("Таблица прогноза"):
                display_cols = ["dt_txt", "main.temp", "main.feels_like", "main.humidity", "wind.speed", "weather.description"]
                show_df = forecast_df[display_cols].rename(
                    columns={
                        "dt_txt": "Время",
                        "main.temp": f"Температура, {units_temp}",
                        "main.feels_like": f"Ощущается, {units_temp}",
                        "main.humidity": "Влажность, %",
                        "wind.speed": f"Ветер, {wind_units}",
                        "weather.description": "Описание",
                    }
                )
                st.dataframe(show_df, use_container_width=True, hide_index=True)

    st.caption("Источник данных: OpenWeather. Приложение: Streamlit + Plotly.")

if __name__ == "__main__":
    main()