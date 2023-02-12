import psycopg
from os import environ
from json import dumps
from random import uniform
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types, utils

conn = psycopg.connect(f"""
    host = {environ.get("DB_HOST")}
    port = {environ.get("DB_PORT")}
    dbname = {environ.get("DB_NAME")}
    user = {environ.get("DB_USER")}
    password = {environ.get("DB_PASSWORD")}
""")

conn.autocommit = True

cur = conn.cursor()

bot = Bot(token = environ.get("BOT_API_TOKEN"), parse_mode = "markdown")
dp = Dispatcher(bot)

@dp.message_handler(commands=["help"])
async def cock_command_handler(message: types.Message):
    message_text = (
        "*Команди бота:*\n"
        "\n/cock - Виростити півня"
        "\n/me - Моя статистика"
        "\n/top - Топ 10 гравців чату"
        "\n/help - Список команд бота"
    )

    await message.reply(message_text) 

@dp.message_handler(
    commands=["cock"], 
    chat_type = [types.ChatType.GROUP, types.ChatType.SUPERGROUP]
)
async def cock_command_handler(message: types.Message):
    user_id = message.from_user.id
    chat = f"chat{message.chat.id}"
    name = message.from_user.full_name

    cur.execute(f"""
        CREATE TABLE if NOT EXISTS "{chat}" (
            id          BIGINT          NOT NULL PRIMARY KEY,
            name        text,
            size        NUMERIC(20, 1),
            history     jsonb,
            last_use    TIMESTAMP(0)    DEFAULT now()
        )
    """)

    size = round(uniform(-5, 10), 1)

    if size < 0:
        message_text = f"розмір твого півня зменшився на *{abs(size)} см*"
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

        cur.execute(f"""
            UPDATE "{chat}" SET name = '{name}'WHERE id = {user_id}
        """) 

        if  midnight > user[4]:
            size += float(user[2])

            cur.execute(f"""
                UPDATE "{chat}" SET
                    name = '{name}',
                    size = {size},
                    history = '{dumps(user[3] | record)}',
                    last_use = '{now}'
                WHERE id = {user_id}
            """) 
        else:
            size = user[2]

            message_text = (
                "твоя спроба вже використана "
                f"""({user[4].strftime("%H:%M")})"""
            )
    else:
        cur.execute(f"""
            INSERT INTO "{chat}"
            VALUES({user_id}, '{name}', {size}, '{dumps(record)}')
        """)

    message_text = (
        f"[{name}](tg://user?id={user_id}), {message_text}"
        f"\nЗараз розмір твого півня *{round(float(size), 1)} см*"
        "\nНаступна спроба завтра"
    )

    await message.reply(message_text)

@dp.message_handler(
    commands=["me"], 
    chat_type = [types.ChatType.GROUP, types.ChatType.SUPERGROUP]
)
async def me_command_handler(message: types.Message):
    try:
        user_id = message.from_user.id
        chat_id = abs(message.chat.id)
        name = message.from_user.full_name
        message_text =  f"[{name}](tg://user?id={user_id}), "

        cur.execute(f"""
            SELECT size, last_use FROM "chat-{chat_id}" WHERE id = {user_id}
        """)

        user = cur.fetchone()

        if user:
        
            cur.execute(f"""
                UPDATE "chat-{chat_id}" SET name = '{name}'WHERE id = {user_id}
            """) 
        
            message_text += (
                "твоя статистика:\n"
                f"\nID чату: `{chat_id}`"
                f"\nID користувача: `{user_id}`"
                f"\nРозмір півня: *{user[0]} см*"
                f"""\nОстання спроба: *{user[1].strftime("%d.%m.%Y %H:%M")}*"""
            )

        else:
            raise Exception

    except:
        message_text += "схоже, що ти ще жодного разу не грав в чаті"

    finally:
        await message.reply(message_text)

@dp.message_handler(
    commands=["top"], 
    chat_type = [types.ChatType.GROUP, types.ChatType.SUPERGROUP]
)
async def top_command_handler(message: types.Message):
    try:
        chat = f"chat{message.chat.id}"

        cur.execute(f"""
            SELECT name, size FROM "{chat}" ORDER BY size DESC LIMIT 10
        """)

        rows = cur.fetchall()

        if rows:

            message_text = "Топ 10 гравців чату:\n"

            for i, row in enumerate(rows):
                message_text += f"\n{i + 1}. {row[0]}: {row[1]} см"
        
        else:
            raise Exception

    except:
        message_text = "От халепа! Ніхто в чаті ще не грав"

    finally:
        await message.reply(message_text)

executor.start_polling(dp, skip_updates = True)
conn.close()
