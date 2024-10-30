import sys
import asyncio
import aiohttp
from typing import Literal
from sys_keys import TOKEN, api_key, process_id
from educational_data import functions, DataPath, calculate_chemistry, UserState, task_chemistry
from core import (
    db,
    html,
    SITE,
    OWNER,
    channel,
    security,
    markdown,
    subscribe,
    omsk_time,
    get_users,
    set_version,
    get_version,
    resources_path
)

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup as IMarkup
from aiogram.types import InlineKeyboardButton as IButton
from aiogram.types import (
    Message,
    FSInputFile,
    CallbackQuery,
    ReplyKeyboardRemove,
)

bot = Bot(TOKEN)
dp = Dispatcher()


# Класс с глобальными переменными для удобного пользования
class Data:
    users = set()


# Метод для добавления и изменения "знакомых"
@dp.message(Command('new_acquaintance'))
@security()
async def _new_acquaintance(message: Message):
    if await developer_command(message): return
    if message.reply_to_message and message.reply_to_message.caption:
        id = int(message.reply_to_message.caption.split('\n', 1)[0].replace("ID: ", ""))
        name = message.text.split(maxsplit=1)[1]
    else:
        id, name = message.text.split(maxsplit=2)[1:]
    if await db.execute("SELECT id FROM acquaintances WHERE id=?", (id,)):
        await db.execute("UPDATE acquaintances SET name=? WHERE id=?", (name, id))
        await message.answer("Данные знакомого изменены")
    else:
        await db.execute("INSERT INTO acquaintances VALUES(?, ?)", (id, name))
        await message.answer("Добавлен новый знакомый!")


# Метод для отправки сообщения от имени бота
@dp.message(F.reply_to_message.__and__(F.chat.id == OWNER).__and__(F.reply_to_message.text.startswith("ID")))
@security()
async def _sender(message: Message):
    user_id = int(message.reply_to_message.text.split('\n', 1)[0].replace("ID: ", ""))
    try:
        copy_message = await bot.copy_message(user_id, OWNER, message.message_id)
    except Exception as e:
        await message.answer(f"Сообщение не отправлено из-за ошибки {e.__class__.__name__}: {e}")
    else:
        await message.answer("Сообщение отправлено")
        await bot.forward_message(OWNER, user_id, copy_message.message_id)


@dp.message(Command('admin'))
@security()
async def _admin(message: Message):
    if await developer_command(message): return
    await message.answer("Команды разработчика:\n"
                         "/reload - перезапустить бота\n"
                         "/stop - остановить бота\n"
                         "/db - база данных бота\n"
                         "/version - изменить версию бота\n"
                         "/new_acquaintance - добавить знакомого")


@dp.message(Command('reload'))
@security()
async def _reload(message: Message):
    if await developer_command(message): return
    if sys.argv[1] == "release":
        await message.answer("*Перезапуск бота*", parse_mode=markdown)
        print("Перезапуск бота")
        await dp.stop_polling()
        asyncio.get_event_loop().stop()  # netangels после остановки фонового процесса автоматически запустит его
    else:
        await message.answer("В тестовом режиме перезапуск бота программно не предусмотрен!")
        print("В тестовом режиме перезапуск бота программно не предусмотрен!")


@dp.message(Command('stop'))
@security()
async def _stop(message: Message):
    if await developer_command(message): return
    await message.answer("*Остановка бота*", parse_mode=markdown)
    print("Остановка бота")
    if sys.argv[1] == "release":
        async with aiohttp.ClientSession() as session:
            async with session.post("https://panel.netangels.ru/api/gateway/token/",
                                    data={"api_key": api_key}) as response:
                token = (await response.json())['token']
                await session.post(f"https://api-ms.netangels.ru/api/v1/hosting/background-processes/{process_id}/stop",
                                   headers={"Authorization": f"Bearer {token}"})
    else:
        await dp.stop_polling()
        asyncio.get_event_loop().stop()


@dp.message(Command('db'))
@security()
async def _db(message: Message):
    if await developer_command(message): return
    await message.answer_document(FSInputFile(resources_path(db.db_path)))


@dp.message(Command('feedback'))
@security('state')
async def _start_feedback(message: Message, state: FSMContext):
    if await new_message(message): return
    await state.set_state(UserState.feedback)
    markup = IMarkup(inline_keyboard=[[IButton(text="❌", callback_data="stop_feedback")]])
    await message.answer("Отправьте текст вопроса или предложения. Любое следующее сообщение будет считаться отзывом",
                         reply_markup=markup)


@dp.message(UserState.feedback)
@security('state')
async def _feedback(message: Message, state: FSMContext):
    if await new_message(message, forward=False): return
    await state.clear()
    acquaintance = await username_acquaintance(message)
    acquaintance = f"<b>Знакомый: {acquaintance}</b>\n" if acquaintance else ""
    await bot.send_photo(OWNER,
                         photo=FSInputFile(resources_path("feedback.png")),
                         caption=f"ID: {message.chat.id}\n"
                                 f"{acquaintance}" +
                                 (f"USERNAME: @{message.from_user.username}\n" if message.from_user.username else "") +
                                 f"Имя: {message.from_user.first_name}\n" +
                                 (f"Фамилия: {message.from_user.last_name}\n" if message.from_user.last_name else "") +
                                 f"Время: {omsk_time(message.date)}",
                         parse_mode=html)
    await message.forward(OWNER)
    await message.answer("Большое спасибо за отзыв!❤️❤️❤️")


@dp.callback_query(F.data == "sop_feedback")
@security('state')
async def _stop_feedback(callback_query: CallbackQuery, state: FSMContext):
    if await new_callback_query(callback_query): return
    await state.clear()
    await callback_query.message.edit_text("Отправка отзыва отменена")


@dp.message(Command('version'))
@security()
async def _version(message: Message):
    if message.text != '/version':
        if await developer_command(message): return
        version = message.text.split(" ", 1)[1]
        await set_version(version)
        await message.answer("Версия бота изменена")
    else:
        if await new_message(message): return
        version = await get_version()
        await message.answer(f"Версия: {version}\n<a href='{SITE}/{version}'>Обновление</a> 👇", parse_mode=html)


@dp.callback_query(F.data == 'subscribe')
@security()
async def _check_subscribe(callback_query: CallbackQuery):
    if await new_callback_query(callback_query, check_subscribe=False): return
    if (await bot.get_chat_member(channel, callback_query.message.chat.id)).status == 'left':
        await callback_query.answer("Вы не подписались на наш канал😢", True)
        await callback_query.bot.send_message(OWNER, "Пользователь не подписался на канал")
    else:
        await callback_query.answer("Спасибо за подписку!❤️ Продолжайте пользоваться ботом", True)
        await callback_query.bot.send_message(OWNER, "Пользователь подписался на канал. Ему предоставлен полный доступ")


@dp.message(CommandStart())
async def _start(message: Message, state: FSMContext):
    if await new_message(message): return
    await state.clear()
    await (await message.answer("...Удаление клавиатурных кнопок...", reply_markup=ReplyKeyboardRemove())).delete()
    markup = IMarkup(inline_keyboard=[[IButton(text="Мои функции", callback_data="help")]])
    await message.answer(f"Привет, {await username_acquaintance(message, 'first_name')}\n"
                         f"[tgmaksim.ru]({SITE})",
                         parse_mode=markdown, reply_markup=markup)
    if message.text == "/start calculate_chemistry":
        await message.answer("Команда /calculate_chemistry и /task_chemistry рассчитывают значения по химии "
                             "(молекулярную массу, массовую долю, молярный объем), уравнивают коэффициенты в "
                             "уравнении реакции и могут расставить индексы в веществе")
    elif message.text == "/start setting_coefficients":
        await state.set_state(UserState.setting_coefficients)
        await message.answer("Отправьте уравнение реакции, в которой необходимо расставить "
                             "коэффициенты. Например: `C + O2 = CO2`", parse_mode=markdown)
    elif message.text == "/start formulation_of_chemical_formulas":
        await state.set_state(UserState.formulation_of_chemical_formulas)
        await message.answer("Отправьте формулу вещества, в котором необходимо расставить "
                             "индексы. Например: `HO`", parse_mode=markdown)


@dp.message(Command('help'))
@security()
async def _help(message: Message):
    if await new_message(message): return
    await help(message)


@dp.callback_query(F.data == "help")
@security()
async def _help_button(callback_query: CallbackQuery):
    if await new_callback_query(callback_query): return
    await callback_query.message.edit_reply_markup()
    await help(callback_query.message)


async def help(message: Message):
    await message.answer("/feedback - оставить отзыв или предложение\n"
                         "/calculate_chemistry - вычисление величин в химии\n"
                         "/task_chemistry - решение задач по химии\n"
                         "/physics7 - физика 7 класса\n"
                         "/physics8 - физика 8 класса\n"
                         "/chemistry8 - химия 8 класса\n"
                         "/mendeleev_table - таблица Менделеева\n"
                         "/valence_table - таблица валентности\n"
                         "/names_compound - таблица названий ионов и их валентности\n"
                         "/density - таблица плотности\n"
                         "/prefixes - таблица значений приставок\n"
                         "/fuel - таблица удельной теплоты сгорания топлива\n"
                         "/heat_capacity - таблица удельной теплоемкости\n"
                         "/melting - таблица удельной теплоты плавления и кристаллизации\n"
                         "/vaporization - таблица удельной теплоты парообразования и конденсации\n"
                         f"<a href='{SITE}'>tgmaksim.ru</a>", parse_mode=html)


@dp.message(Command('density'))
@security()
async def _density(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Density/density.png")))


@dp.message(Command('fuel'))
@security()
async def _fuel(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Thermal Phenomena/fuel.png")))


@dp.message(Command('heat_capacity'))
@security()
async def _heat_capacity(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Thermal Phenomena/heat_capacity.png")))


@dp.message(Command('melting'))
@security()
async def _melting(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Thermal Phenomena/melting.png")))


@dp.message(Command('vaporization'))
@security()
async def _vaporization(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Thermal Phenomena/vaporization.png")))


@dp.message(Command('mendeleev_table'))
@security()
async def _mendeleev_table(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Chemistry/main_chemistry_table.png")))


@dp.message(Command('valence_table'))
@security()
async def _valence_table(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Chemistry/valence_table (1).png")))
    await message.answer_photo(FSInputFile(resources_path("Chemistry/valence_table (2).png")))


@dp.message(Command('names_compounds'))
@security()
async def _names_compounds(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Chemistry/names_compounds (1).png")))
    await message.answer_photo(FSInputFile(resources_path("Chemistry/names_compounds (2).png")))


@dp.message(Command('names_acids'))
@security()
async def _names_acids(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path('Chemistry/names_acids.png')))


@dp.message(Command('prefixes'))
@security()
async def _prefixes(message: Message):
    if await new_message(message): return
    await message.answer_photo(FSInputFile(resources_path("Prefixes/prefixes.png")))


@dp.message(Command('physics7', 'physics8', 'chemistry8', 'calculate_chemistry', 'task_chemistry'))
@security()
async def _start_educational_functions(message: Message):
    if await new_message(message): return
    await functions[message.text.replace('/', '', 1)](message, True)


@dp.callback_query(F.data == "stop")
@security()
async def _stop(callback_query: CallbackQuery):
    if await new_callback_query(callback_query): return
    await callback_query.message.edit_reply_markup()
    await callback_query.message.edit_text("Функция остановлена!")


def decor_new_message(fun):
    async def new(message: Message, state: FSMContext):
        if await new_message(message): return
        await fun(message, state)

    return new


def decor_new_callback_query(fun):
    async def new(callback_query: CallbackQuery, state: FSMContext):
        if await new_callback_query(callback_query): return
        await fun(callback_query, state)

    return new


dp.message(UserState.molecular_weight)(decor_new_message(calculate_chemistry.molecular_weight))
dp.message(UserState.mass_fraction1)(decor_new_message(calculate_chemistry.mass_fraction1))
dp.callback_query(UserState.mass_fraction2)(decor_new_callback_query(calculate_chemistry.mass_fraction2))
dp.message(UserState.volume_fraction1)(decor_new_message(calculate_chemistry.volume_fraction1))
dp.message(UserState.volume_fraction2)(decor_new_message(calculate_chemistry.volume_fraction2))
dp.message(UserState.amount_of_substance_from_mass1)(
    decor_new_message(calculate_chemistry.amount_of_substance_from_mass1))
dp.message(UserState.amount_of_substance_from_mass2)(
    decor_new_message(calculate_chemistry.amount_of_substance_from_mass2))
dp.message(UserState.amount_of_substance_from_number_of_particles)(
    decor_new_message(calculate_chemistry.amount_of_substance_from_number_of_particles))
dp.message(UserState.amount_of_substance_from_volume_of_gas)(
    decor_new_message(calculate_chemistry.amount_of_substance_from_volume_of_gas))
dp.message(UserState.gas_density)(decor_new_message(calculate_chemistry.gas_density))
dp.message(UserState.formulation_of_chemical_formulas)(
    decor_new_message(task_chemistry.formulation_of_chemical_formulas))
dp.message(UserState.making_formulas_by_name)(decor_new_message(task_chemistry.making_formulas_by_name))
dp.message(UserState.setting_coefficients)(decor_new_message(task_chemistry.setting_coefficients))


@dp.callback_query(F.data.startswith('task_chemistry').__or__(F.data.startswith('calculate_chemistry')))
@security('state')
async def _educational_functions(callback_query: CallbackQuery, state: FSMContext):
    if await new_callback_query(callback_query): return
    await callback_query.message.edit_text(DataPath(*callback_query.data.split(".")).data.text)
    await DataPath(*callback_query.data.split(".")).data(callback_query.message, state)


@dp.callback_query()
@security()
async def _educational_data(callback_query: CallbackQuery):
    if await new_callback_query(callback_query): return
    new = False
    callback_query_data = callback_query.data
    if callback_query_data.startswith("_del"):
        await callback_query.message.delete()
        new = True
        callback_query_data = callback_query_data.replace("_del", "", 1)
    await DataPath(*callback_query_data.split(".")).data(callback_query.message, new)


@dp.callback_query()
@security()
async def _other_callback_query(callback_query: CallbackQuery):
    await new_callback_query(callback_query)


@dp.message()
@security()
async def _other_messages(message: Message):
    await new_message(message)


async def new_user(message: Message):
    if not await db.execute("SELECT id FROM users WHERE id=?", (str(message.chat.id),)):
        await db.execute("INSERT INTO users VALUES(?, ?)", (message.chat.id, ""))
        Data.users.add(message.chat.id)
    await db.execute("UPDATE users SET last_message=? WHERE id=?", (str(omsk_time(message.date)), message.chat.id))


async def username_acquaintance(message: Message, default: Literal[None, 'first_name'] = None):
    id = message.chat.id
    user = await db.execute("SELECT name FROM acquaintances WHERE id=?", (id,))
    if user:
        return user[0][0]
    return message.from_user.first_name if default == 'first_name' else None


async def developer_command(message: Message) -> bool:
    if message.chat.id == OWNER:
        await new_message(message, False)
        await message.answer("*Команда разработчика активирована!*", parse_mode=markdown)
    else:
        await new_message(message)
        await message.answer("*Команда разработчика НЕ была активирована*", parse_mode=markdown)

    return message.chat.id != OWNER


async def subscribe_to_channel(message: Message):
    if (await bot.get_chat_member(channel, message.from_user.id)).status == 'left' and not message.text.startswith('/start'):
        markup = IMarkup(
            inline_keyboard=[[IButton(text="Подписаться на канал", url=subscribe)],
                             [IButton(text="Подписался", callback_data="subscribe")]])
        await message.answer("Бот работает только с подписчиками моего канала. "
                             "Подпишитесь и получите полный доступ к боту", reply_markup=markup)
        await message.bot.send_message(OWNER, "Пользователь не подписан на наш канал, доступ ограничен!")
        return False
    return True


async def new_message(message: Message, /, forward: bool = True) -> bool:
    if message.content_type == "text":
        content = message.text
    elif message.content_type == "web_app_data":
        content = message.web_app_data.data
    else:
        content = f"<{message.content_type}>"
    id = str(message.chat.id)
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    date = str(omsk_time(message.date))
    acquaintance = await username_acquaintance(message)
    acquaintance = f"<b>Знакомый: {acquaintance}</b>\n" if acquaintance else ""

    await db.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                     (id, username, first_name, last_name, content, date))

    if message.chat.id == OWNER:
        return False

    if message.content_type not in ("text", "web_app_data"):  # Если сообщение не является текстом или ответом mini app
        await bot.send_message(
            OWNER,
            text=f"ID: {id}\n"
                 f"{acquaintance}" +
                 (f"USERNAME: @{username}\n" if username else "") +
                 f"Имя: {first_name}\n" +
                 (f"Фамилия: {last_name}\n" if last_name else "") +
                 f"Время: {date}",
            parse_mode=html)
        await message.forward(OWNER)
    elif forward or (message.entities and message.entities[0].type != 'bot_command'):  # Если сообщение содержит форматирование или необходимо переслать сообщение
        if message.entities and message.entities[0].type != 'bot_command':
            await bot.send_message(
                OWNER,
                text=f"ID: {id}\n"
                     f"{acquaintance}" +
                     (f"USERNAME: @{username}\n" if username else "") +
                     f"Имя: {first_name}\n" +
                     (f"Фамилия: {last_name}\n" if last_name else "") +
                     f"Время: {date}",
                parse_mode=html)
            await message.forward(OWNER)
        else:  # Если сообщение не содержит форматирование и его не нужно пересылать
            try:
                await bot.send_message(
                    OWNER,
                    text=f"ID: {id}\n"
                         f"{acquaintance}" +
                         (f"USERNAME: @{username}\n" if username else "") +
                         f"Имя: {first_name}\n" +
                         (f"Фамилия: {last_name}\n" if last_name else "") +
                         (f"<code>{content}</code>\n"
                          if not content.startswith("/") or len(content.split()) > 1 else f"{content}\n") +
                         f"Время: {date}",
                    parse_mode=html)
            except:
                await bot.send_message(
                    OWNER,
                    text=f"ID: {id}\n"
                         f"{acquaintance}" +
                         (f"USERNAME: @{username}\n" if username else "") +
                         f"Имя: {first_name}\n" +
                         (f"Фамилия: {last_name}\n" if last_name else "") +
                         f"<code>{content}</code>\n"
                         f"Время: {date}",
                    parse_mode=html)
                await message.forward(OWNER)

    if message.chat.id not in Data.users:
        await message.forward(OWNER)
    await new_user(message)

    return not await subscribe_to_channel(message)


async def new_callback_query(callback_query: CallbackQuery, /, check_subscribe: bool = True) -> bool:
    message = callback_query.message
    id = str(message.chat.id)
    username = callback_query.from_user.username
    first_name = callback_query.from_user.first_name
    last_name = callback_query.from_user.last_name
    callback_data = callback_query.data
    date = str(omsk_time(message.date))
    acquaintance = await username_acquaintance(message)
    acquaintance = f"<b>Знакомый: {acquaintance}</b>\n" if acquaintance else ""

    await db.execute("INSERT INTO callbacks_query VALUES (?, ?, ?, ?, ?, ?)",
                     (id, username, first_name, last_name, callback_data, date))

    if callback_query.from_user.id != OWNER:
        await bot.send_message(
            OWNER,
            text=f"ID: {id}\n"
                 f"{acquaintance}" +
                 (f"USERNAME: @{username}\n" if username else "") +
                 f"Имя: {first_name}\n" +
                 (f"Фамилия: {last_name}\n" if last_name else "") +
                 f"CALLBACK_DATA: {callback_data}\n"
                 f"Время: {date}",
            parse_mode=html)

    if check_subscribe and not await subscribe_to_channel(message):
        await callback_query.message.edit_reply_markup()
        return True
    return False


async def start_bot():
    await db.execute("CREATE TABLE IF NOT EXISTS messages (id TEXT, username TEXT, first_name TEXT, last_name TEXT, "
                     "message_text TEXT, datetime TEXT)")
    await db.execute("CREATE TABLE IF NOT EXISTS callbacks_query (id TEXT, username TEXT, first_name TEXT, "
                     "last_name TEXT, callback_data TEXT, datetime TEXT)")
    await db.execute("CREATE TABLE IF NOT EXISTS system_data (key TEXT, value TEXT)")
    await db.execute("CREATE TABLE IF NOT EXISTS acquaintances (id TEXT, username TEXT, first_name TEXT, "
                     "last_name TEXT, name TEXT)")
    await db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT, last_message TEXT)")
    if not await db.execute("SELECT value FROM system_data WHERE key=?", ("version",)):
        await db.execute("INSERT INTO system_data VALUES(?, ?)", ("version", "0.0"))

    Data.users = await get_users()

    await bot.send_message(OWNER, f"*Бот запущен!🚀*", parse_mode=markdown)
    print("Запуск бота")
    await dp.start_polling(bot)


def check_argv():
    program_variant = sys.argv[1]
    if program_variant not in ("release", "debug"):
        raise TypeError("Выберите вариант запуска программы: release или debug")


if __name__ == '__main__':
    check_argv()
    asyncio.run(start_bot())
