import sys
import threading
from datetime import datetime
import aiosqlite as sl
import asyncio
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils import executor
import logging
from aiogram import Bot as tBot, Dispatcher, types

time1 = datetime.today().timestamp()
logging.basicConfig(level=logging.WARNING, filename='wy_log.txt', format='%(asctime)s %(levelname)s:%(message)s')
SITE = "ru.wikipedia.org"

import editsFinder

API_KEY = "API_KEY"
bot = tBot(token=API_KEY)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.WARNING, filename='wy_log.txt', format='%(asctime)s %(levelname)s:%(message)s')
sys.stderr = open('wy_log.txt', 'a')
DB = "maindata.sqlite"
PASSWORD = "PASSWORD"
HINT = "HINT"
available_users = set()

#Отправка сообщения
async def write_msg(message, user_id):
  try:
    await bot.send_message(user_id, message)
  except Exception as e:
    logging.warning(f"Сообщение для {user_id} не отправлено")
    logging.warning(e)

class BotState(StatesGroup):
  addUser = State()
  removeUser = State()
  access = State()

async def get_users():
  global available_users
  async with sl.connect(DB) as con:
    cursor = await con.execute(f'SELECT id FROM users')
    users = await cursor.fetchall()
  available_users = set([user[0] for user in users])

async def on_startup(x):
  asyncio.create_task(get_users())

# Поставить наблюдение за правками на паузу (или возобновить)
async def wikipause(id, bool: bool):
  try:
    async with sl.connect(DB) as con:
      await con.execute(f'UPDATE main SET paused = {bool} where id = {id}')
      await con.commit()
  except Exception as e:
    logging.warning(e)

#Сброс состояния бота.
@dp.message_handler(commands=['cancel'], state=BotState.all_states)
async def cancel(result: types.Message, state: FSMContext):
  await state.reset_state()
  await result.reply(f"Бот возвращён в начальное состояние")

# Вход в режим добавления в список наблюдения
@dp.message_handler(commands=['add'])
async def addingStart(message: types.Message):
  id = message.from_user.id
  if id not in available_users:
    return
  await write_msg("введите название страницы", id)
  await BotState.addUser.set()


# Добавление пользователя в список наблюдения
@dp.message_handler(state=BotState.addUser)
async def addUser(message: types.Message, state: FSMContext):
  id = message.from_user.id
  username = "\"" + message.text + "\""
  try:
    async with sl.connect(DB) as con:
      await con.execute(f'INSERT INTO main (id, wikiuser) values({id},{username})')
      await con.commit()
    await write_msg("^_^", id)
  except Exception as e:
    logging.warning(e)
  await state.reset_state()


# Вход в режим удаления из списка наблюдения
@dp.message_handler(commands=['delete'])
async def deleteStart(message: types.Message):
  id = message.from_user.id
  if id not in available_users:
    return
  await write_msg("введите название страницы", id)
  await BotState.removeUser.set()


# Удаление пользователя из списка наблюдения
@dp.message_handler(state=BotState.removeUser)
async def deleteUser(message: types.Message, state: FSMContext):
  id = message.from_user.id
  username = "\"" + message.text + "\""
  try:
    async with sl.connect(DB) as con:
      await con.execute(f'DELETE FROM main where id={id} and wikiuser={username}')
      await con.commit()
    await write_msg("^_^", id)
  except Exception as e:
    logging.warning(e)
  await state.reset_state()


# Получение списка наблюдения
@dp.message_handler(commands=['list'])
async def deleteStart(message: types.Message):
  id = message.from_user.id
  if id not in available_users:
    return
  async with sl.connect(DB) as con:
    cursor = await con.execute(f'SELECT wikiuser FROM main where id={id}')
    result = await cursor.fetchall()
  if result:
    text = "\n".join([line[0] for line in result])
  else:
    text = "пустой лист"
  await write_msg(text, id)


# Очищение списка наблюдения
@dp.message_handler(commands=['clear'])
async def deleteStart(message: types.Message):
  id = message.from_user.id
  if id not in available_users:
    return
  try:
    async with sl.connect(DB) as con:
      await con.execute(f'DELETE FROM main where id={id}')
      await con.commit()
    await write_msg("^_^", id)
  except Exception as e:
    logging.warning(e)


# Пауза/возобновление наблюдение
@dp.message_handler(commands=['pause'])
async def deleteStart(message: types.Message):
  id = message.from_user.id
  if id not in available_users:
    return
  try:
    async with sl.connect(DB) as con:
      cursor = await con.execute(f'SELECT paused FROM main where id={id}')
      row = await cursor.fetchone()
    await wikipause(id, not bool(*row))
    await write_msg("^_^", id)
  except Exception as e:
    logging.warning(e)

# Получение доступа к боту - запрос пароля
@dp.message_handler(commands=['access'])
async def startAccess(message: types.Message):
  if not available_users or message.from_user.id not in available_users:
    await write_msg("Введите пароль", message.from_user.id)
    await BotState.access.set()
    return
  await write_msg("Вы уже получили доступ к боту", message.from_user.id)

# Получение доступа к боту - получение пароля
@dp.message_handler(state=BotState.access)
async def getAccess (message: types.Message, state: FSMContext):
  if message.text==PASSWORD:
    user = message.from_user.id
    try:
      async with sl.connect(DB) as con:
        await con.execute(f'INSERT INTO users VALUES (?)', (user,))
        await con.commit()
      await message.reply("Вам предоставлен доступ к боту")
      available_users.add(user)
    except:
      logging.warning(f"Произошла ошибка про получении доступа к боту участником {user}")
    finally:
      await state.reset_state()
    return
  await message.reply(f"Пароль неверный. Подсказка: {HINT}")

if __name__ == '__main__':
  threading.Thread(target=editsFinder.start).start()
  executor.start_polling(dp, on_startup=on_startup)
