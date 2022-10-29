import asyncio
import logging
import time
from datetime import datetime

import aioschedule
from mwclient import Site
import aiosqlite as sl
from wikiyandere import DB, bot
time1 = datetime.today().timestamp()
logging.basicConfig(level=logging.WARNING, filename='wy_log.txt', format='%(asctime)s %(levelname)s:%(message)s')
SITE = "ru.wikipedia.org"

#Отправка сообщения
async def write_msg(message, user_id):
  try:
    await bot.send_message(user_id, message)
  except Exception as e:
    logging.warning(f"Сообщение для {user_id} не отправлено")
    logging.warning(e)

#Получение новых правок одного пользователя
async def getLastEdits(botUser, wikiUser):
  try:
    site = Site(SITE)
    fullist = site.usercontributions(wikiUser, end=time1, prop="sizediff|title|comment|ids")
    logging.info("время задано")
    if fullist:
      for edits in fullist:
        title = edits[
          "title"].replace(" ", "_")
        await write_msg(edits[
                          "user"] + "\n" + "https://ru.wikipedia.org/w/index.php?title=" + title + "&diff=" + str(
          edits["revid"]) + "&oldid=" + str(
          edits["parentid"]) + "\n" + "размер: " + str(
          edits["sizediff"]) + "\n" + "комментарий: " + edits["comment"], botUser)
  except Exception as e:
    logging.warning(f"Не удалось получить правки для участника {wikiUser}")
    logging.warning(e)

#Получение новых правок для всех пользователей
async def getnewedits():
  global time1
  async with sl.connect(DB) as con:
    cursor = await con.execute('SELECT * FROM main')
    maindata = await cursor.fetchall()
  loop = asyncio.get_event_loop()
  if not maindata:
    time1 = datetime.today().timestamp()
    return
  coroutines = [getLastEdits(data[0],data[1]) for data in maindata if not data[2]]
  await asyncio.gather(*coroutines)
  time1 = datetime.today().timestamp()


def start():
  aioschedule.every().minute.do(getnewedits)
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  while True:
    loop.run_until_complete(aioschedule.run_pending())
    time.sleep(0.1)
