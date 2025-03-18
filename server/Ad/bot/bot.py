import telebot
import requests
import time
from bs4 import BeautifulSoup

# Телеграм токен и канал
TOKEN = "7617191140:AAEe9_mgKdS7pxdwNorlIJw4da1AHiiabAw"
CHANNEL_ID = "@news_orbit_24"
BASE_URL = "http://127.0.0.1:8000/"

bot = telebot.TeleBot(TOKEN)


def parser(target_index):
    page = requests.get(BASE_URL)
    soup = BeautifulSoup(page.content, "html.parser")

    # Ищем все новости
    news_items = soup.find_all("div", class_="news-item")
    if not news_items:
        return None

    # Ищем нужную новость по data-index
    for news in news_items:
        if "data-index" in news.attrs and news["data-index"] == str(target_index):
            title_tag = news.find("h2")
            description_tag = news.find("p")
            url_tag = news.find("a", href=True)

            title = title_tag.text.strip() if title_tag else "Нет заголовка"
            description = description_tag.text.strip() if description_tag else "Нет описания"
            url = url_tag["href"].strip() if url_tag and url_tag["href"] else BASE_URL

            return title, description, url
    return None


@bot.message_handler(content_types=['text'])
def commands(message):
    if message.text.lower() == "старт":
        for index in range(10):
            news = parser(index)
            if news:
                title, description, url = news
                bot.send_message(CHANNEL_ID, f"{title}\n\n{description}\n\n{url}")
                time.sleep(60)

        bot.send_message(CHANNEL_ID, "Все новости отправлены. Бот завершает работу.")
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши 'Старт'")


bot.polling()
