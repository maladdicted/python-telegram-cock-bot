import psycopg
from os import environ
from json import dumps
from random import uniform
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types, utils

conn = psycopg.connect(f"""
        host={environ.get("DB_HOST")}
        port={environ.get("DB_PORT")}
        dbname={environ.get("DB_NAME")}
        user={environ.get("DB_USER")}
        password={environ.get("DB_PASSWORD")}
    """)

conn.autocommit = True

cur = conn.cursor()

bot = Bot(token = environ.get("BOT_API_TOKEN"))
dp = Dispatcher(bot)

@dp.message_handler(
    commands=["cock"], 
    chat_type = [types.ChatType.GROUP, types.ChatType.SUPERGROUP]
    )
async def cock_command_handler(message: types.Message):
    user_id = message.from_user.id
    chat = f"chat{message.chat.id}"

    cur.execute(f"""CREATE TABLE if NOT EXISTS "{chat}" (
            id          BIGINT          NOT NULL PRIMARY KEY,
            size        NUMERIC(20, 1),
            history     jsonb,
            last_use    TIMESTAMP(0)    DEFAULT now()
        )""")

    size = round(uniform(-5, 10), 1)

    if size < 0:
        message_text = f"розмір твого півня зменшився на *{size} см*"
    elif size > 0:
        message_text = f"розмір твого півня збільшився на *{size} см*"
    else:
        message_text = "розмір твого півня не змінився"

    cur.execute(f"""SELECT * FROM "{chat}" WHERE id = {user_id}""") 
    user = cur.fetchone()
    now = datetime.now()
    midnight = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    record = {now.strftime("%Y-%m-%d %H:%M:%S"): size}

    if user:
        if  midnight > user[3]:
            size += round(float(user[1]), 1)

            cur.execute(f"""
                UPDATE "{chat}" SET
                    size = {size},
                    history = '{dumps(user[2] | record)}',
                    last_use = '{now}'
                WHERE id = {user_id}
            """) 
        else:
            size = user[1]
            message_text = "твоя спроба вже використана"
    else:
        cur.execute(f"""
            INSERT INTO "{chat}" VALUES({user_id}, {size}, '{dumps(record)}')
        """)

    message_text = (
            f"[{message.from_user.full_name}](tg://user?id={user_id}), "
            f"{message_text}"
            f"\nЗараз розмір твого півня *{size} см*"
            "\nНаступна спроба завтра"
        )

    await message.reply(
            message_text, 
            parse_mode = types.message.ParseMode.MARKDOWN
        )

executor.start_polling(dp, skip_updates = True)
conn.close()
