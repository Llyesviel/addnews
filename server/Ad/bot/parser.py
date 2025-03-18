import requests
from bs4 import BeautifulSoup

URL = "http://127.0.0.1:8000/"

page = requests.get(URL)
soup = BeautifulSoup(page.content, "html.parser")

# Находим первую новость
post = soup.find("div", class_="news-item")

if post:
    title_tag = post.find("h2")
    description_tag = post.find("p")
    url_tag = post.find("a", href=True)

    title = title_tag.text.strip() if title_tag else "Нет заголовка"
    description = description_tag.text.strip() if description_tag else "Нет описания"
    url = url_tag["href"].strip() if url_tag else "Ссылка отсутствует"

    print(f"Заголовок: {title}")
    print(f"Описание: {description}")
    print(f"Ссылка: {url}")
else:
    print("Новости не найдены")
