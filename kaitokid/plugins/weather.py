import aiohttp
import logging
from logging import getLogger

from pyrogram import filters
from kaitokid import app
from kaitokid.vars import COMMAND_HANDLER
from datetime import datetime

LOGGER = getLogger("KaitoKid")

API_KEY = ""  # Thay bằng API Key của OpenWeatherMap

# Hàm lấy tọa độ từ tên thành phố
async def get_coordinates(city):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    return data[0]['lat'], data[0]['lon']
            return None, None

# Hàm lấy dữ liệu thời tiết từ API onecall
async def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&units=metric&lang=vi&appid={API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

# Hàm xử lý lệnh thời tiết
@app.on_message(filters.command("thoitiet", COMMAND_HANDLER))
async def weather_command(client, message):
    command = message.text.split(maxsplit=1)
    city = command[1] if len(command) > 1 else None

    # Mặc định là Hà Nội và TP.HCM nếu không có từ khóa
    if not city:
        cities = ["Hà Nội", "Thành phố Hồ Chí Minh"]
        response_messages = []

        for city in cities:
            lat, lon = await get_coordinates(city)
            if lat is not None and lon is not None:
                weather_data = await get_weather(lat, lon)
                if weather_data:
                    response_messages.append(format_weather_message(city, weather_data))
            else:
                response_messages.append(f"⚠️ Không tìm thấy tọa độ cho thành phố: {city}")

        response_messages.append("🌍 Bạn có thể nhập tên thành phố để xem thời tiết nơi khác.")
        await message.reply("\n\n".join(response_messages))
        return

    # Tìm kiếm thời tiết cho thành phố cụ thể
    lat, lon = await get_coordinates(city)
    if lat is not None and lon is not None:
        weather_data = await get_weather(lat, lon)
        if weather_data:
            weather_message = format_weather_message(city, weather_data)
            await message.reply(weather_message)
        else:
            await message.reply("⚠️ Không tìm thấy thông tin thời tiết cho thành phố này. Vui lòng thử lại.")
    else:
        await message.reply("⚠️ Không tìm thấy tọa độ cho thành phố này.")

# Hàm định dạng thông tin thời tiết để gửi về
def format_weather_message(city, data):
    current_weather = data['current']
    weather_description = current_weather['weather'][0]['description'].capitalize()
    temperature = current_weather['temp']
    feels_like = current_weather['feels_like']
    humidity = current_weather['humidity']
    wind_speed = current_weather['wind_speed']

    # Thông tin thời tiết cho 5 ngày tiếp theo
    daily_forecast = data['daily'][1:6]
    forecast_message = "\n\nThời tiết 5 ngày tới:\n"
    for day in daily_forecast:
        date = datetime.fromtimestamp(day['dt']).strftime('%d/%m/%Y')
        day_weather = day['weather'][0]['description'].capitalize()
        min_temp = day['temp']['min']
        max_temp = day['temp']['max']
        forecast_message += f"- {date}: {day_weather} - {min_temp}°C đến {max_temp}°C\n"

    suggestions = []
    if temperature < 20:
        suggestions.append("Nên mặc ấm để tránh lạnh.")
    elif temperature > 30:
        suggestions.append("Hãy uống nhiều nước và tránh nắng gắt.")

    return (
        f"\U0001F324️ Thời tiết tại {city}:\n\n"
        f"- Mô tả: {weather_description}\n"
        f"- Nhiệt độ hiện tại: {temperature}°C (Cảm giác: {feels_like}°C)\n"
        f"- Độ ẩm: {humidity}%\n"
        f"- Tốc độ gió: {wind_speed} m/s\n"
        f"{forecast_message}"
        + ("\n" + " ".join(suggestions) if suggestions else "")
    )