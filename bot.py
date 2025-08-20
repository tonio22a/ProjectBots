from logic import DB_Manager
from config import *
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telebot import types

# Инициализация бота и вспомогательных объектов
bot = TeleBot(TOKEN)
hideBoard = types.ReplyKeyboardRemove()  # Объект для скрытия клавиатуры
manager = DB_Manager(DATABASE)  # Менеджер работы с БД

# Константы
cancel_button = "Отмена 🚫"
attributes_of_projects = {
    'Имя проекта': ["Введите новое имя проекта", "project_name"],
    "Описание": ["Введите новое описание проекта", "description"],
    "Ссылка": ["Введите новую ссылку на проект", "url"],
    "Статус": ["Выберите новый статус задачи", "status_id"]
}

## Вспомогательные функции

def cansel(message):
    """Обработка отмены действия"""
    bot.send_message(message.chat.id, "❗ Чтобы посмотреть команды, используй - /info", reply_markup=hideBoard)

def no_projects(message):
    """Сообщение об отсутствии проектов"""
    bot.send_message(message.chat.id, '❗ У тебя пока нет проектов!\nМожешь добавить их с помошью команды /new_project')

def gen_inline_markup(rows):
    """Генерация inline-клавиатуры"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    for row in rows:
        markup.add(InlineKeyboardButton(row, callback_data=row))
    return markup

def gen_markup(rows):
    """Генерация reply-клавиатуры (одноразовой)"""
    markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.row_width = 1
    for row in rows:
        markup.add(KeyboardButton(row))
    markup.add(KeyboardButton(cancel_button))
    return markup

def info_project(message, user_id, project_name):
    """Отображение информации о проекте"""
    info = manager.get_project_info(user_id, project_name)[0]
    skills = manager.get_project_skills(project_name)
    if not skills:
        skills = '❗ Навыки пока не добавлены'
    bot.send_message(message.chat.id, f"""Имя проекта: {info[0]}
Описание: {info[1]}
Ссылка: {info[2]}
Статус: {info[3]}
Навыки: {skills}
""")

## Обработчики команд

@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработка команды /start - приветственное сообщение"""
    bot.send_message(message.chat.id, """👋 Привет! Я бот-менеджер проектов
Я помогу тебе сохранить твои проекты и информацию о них!) 
""")
    info(message)

@bot.message_handler(commands=['info'])
def info(message):
    """Обработка команды /info - информация о доступных командах"""
    bot.send_message(message.chat.id,
"""
📋 Вот команды которые могут тебе помочь:

/new_project - используй для добавления нового проекта
/skills - выбор проекта, для которого нужно выбрать навык
/projects - ваши проекты
/delete - удаление проекта
/update_projects - выбор проекта для изменения

❗ Также ты можешь ввести имя проекта и узнать информацию о нем!""")

@bot.message_handler(commands=['new_project'])
def addtask_command(message):
    """Обработка команды /new_project - начало процесса добавления проекта"""
    bot.send_message(message.chat.id, "👨 Введите название проекта:")
    bot.register_next_step_handler(message, name_project)

def name_project(message):
    """Получение названия проекта"""
    name = message.text
    user_id = message.from_user.id
    data = [user_id, name]
    bot.send_message(message.chat.id, "🖇️ Введите ссылку на проект")
    bot.register_next_step_handler(message, link_project, data=data)

def link_project(message, data):
    """Получение ссылки на проект"""
    data.append(message.text)
    statuses = [x[0] for x in manager.get_statuses()] 
    bot.send_message(message.chat.id, "✅ Введите текущий статус проекта", reply_markup=gen_markup(statuses))
    bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)

def callback_project(message, data, statuses):
    """Получение статуса проекта и сохранение в БД"""
    status = message.text
    if message.text == cancel_button:
        cansel(message)
        return
    if status not in statuses:
        bot.send_message(message.chat.id, "❌ Ты выбрал статус не из списка, попробуй еще раз!)", reply_markup=gen_markup(statuses))
        bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)
        return
    status_id = manager.get_status_id(status)
    data.append(status_id)
    manager.insert_project([tuple(data)])
    bot.send_message(message.chat.id, "✅ Проект сохранен")

@bot.message_handler(commands=['skills'])
def skill_handler(message):
    """Обработка команды /skills - выбор проекта для добавления навыков"""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        bot.send_message(message.chat.id, '❗ Выбери проект для которого нужно выбрать навык', reply_markup=gen_markup(projects))
        bot.register_next_step_handler(message, skill_project, projects=projects)
    else:
        no_projects(message)

def skill_project(message, projects):
    """Обработка выбора проекта для навыка"""
    project_name = message.text
    if message.text == cancel_button:
        cansel(message)
        return
        
    if project_name not in projects:
        bot.send_message(message.chat.id, '❗ У тебя нет такого проекта, попробуй еще раз!) Выбери проект для которого нужно выбрать навык', reply_markup=gen_markup(projects))
        bot.register_next_step_handler(message, skill_project, projects=projects)
    else:
        skills = [x[1] for x in manager.get_skills()]
        bot.send_message(message.chat.id, '❗ Выбери навык', reply_markup=gen_markup(skills))
        bot.register_next_step_handler(message, set_skill, project_name=project_name, skills=skills)

def set_skill(message, project_name, skills):
    """Добавление навыка к проекту"""
    skill = message.text
    user_id = message.from_user.id
    if message.text == cancel_button:
        cansel(message)
        return
        
    if skill not in skills:
        bot.send_message(message.chat.id, '❗ Видимо, ты выбрал навык. не из спика, попробуй еще раз!) Выбери навык', reply_markup=gen_markup(skills))
        bot.register_next_step_handler(message, set_skill, project_name=project_name, skills=skills)
        return
    manager.insert_skill(user_id, project_name, skill )
    bot.send_message(message.chat.id, f'✅ Навык {skill} добавлен проекту {project_name}')

@bot.message_handler(commands=['projects'])
def get_projects(message):
    """Обработка команды /projects - вывод списка проектов"""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "\n".join([f"Имя проекта: {x[2]} \nСсылка: {x[4]}\n" for x in projects])
        bot.send_message(message.chat.id, text, reply_markup=gen_inline_markup([x[2] for x in projects]))
    else:
        no_projects(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Обработка inline-кнопок (просмотр информации о проекте)"""
    project_name = call.data
    info_project(call.message, call.from_user.id, project_name)

@bot.message_handler(commands=['delete'])
def delete_handler(message):
    """Обработка команды /delete - удаление проекта"""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "\n".join([f"Имя проекта: {x[2]} \nСсылка: {x[4]}\n" for x in projects])
        projects = [x[2] for x in projects]
        bot.send_message(message.chat.id, text, reply_markup=gen_markup(projects))
        bot.register_next_step_handler(message, delete_project, projects=projects)
    else:
        no_projects(message)

def delete_project(message, projects):
    """Удаление выбранного проекта"""
    project = message.text
    user_id = message.from_user.id

    if message.text == cancel_button:
        cansel(message)
        return
    if project not in projects:
        bot.send_message(message.chat.id, '❗ У тебя нет такого проекта, попробуй выбрать еще раз!', reply_markup=gen_markup(projects))
        bot.register_next_step_handler(message, delete_project, projects=projects)
        return
    project_id = manager.get_project_id(project, user_id)
    manager.delete_project(user_id, project_id)
    bot.send_message(message.chat.id, f'✅ Проект {project} удален!')

@bot.message_handler(commands=['update_projects'])
def update_project(message):
    """Обработка команды /update_projects - начало процесса обновления проекта"""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        bot.send_message(message.chat.id, "❗ Выбери проект, который хочешь изменить", reply_markup=gen_markup(projects))
        bot.register_next_step_handler(message, update_project_step_2, projects=projects )
    else:
        no_projects(message)

def update_project_step_2(message, projects):
    """Выбор проекта для редактирования"""
    project_name = message.text
    if message.text == cancel_button:
        cansel(message)
        return
    if project_name not in projects:
        bot.send_message(message.chat.id, "❗ Что-то пошло не так!) Выбери проект, который хочешь изменить еще раз:", reply_markup=gen_markup(projects))
        bot.register_next_step_handler(message, update_project_step_2, projects=projects )
        return
    bot.send_message(message.chat.id, "❗ Выбери, что требуется изменить в проекте", reply_markup=gen_markup(attributes_of_projects.keys()))
    bot.register_next_step_handler(message, update_project_step_3, project_name=project_name)

def update_project_step_3(message, project_name):
    """Выбор атрибута для редактирования"""
    attribute = message.text
    reply_markup = None 
    if message.text == cancel_button:
        cansel(message)
        return
    if attribute not in attributes_of_projects.keys():
        bot.send_message(message.chat.id, "❗ Кажется, ты ошибся, попробуй еще раз!)", reply_markup=gen_markup(attributes_of_projects.keys()))
        bot.register_next_step_handler(message, update_project_step_3, project_name=project_name)
        return
    elif attribute == "Статус":
        rows = manager.get_statuses()
        reply_markup=gen_markup([x[0] for x in rows])
    bot.send_message(message.chat.id, attributes_of_projects[attribute][0], reply_markup = reply_markup)
    bot.register_next_step_handler(message, update_project_step_4, project_name=project_name, attribute=attributes_of_projects[attribute][1])

def update_project_step_4(message, project_name, attribute): 
    """Сохранение изменений проекта"""
    update_info = message.text
    if attribute == "status_id":
        rows = manager.get_statuses()
        if update_info in [x[0] for x in rows]:
            update_info = manager.get_status_id(update_info)
        elif update_info == cancel_button:
            cansel(message)
        else:
            bot.send_message(message.chat.id, "❗ Был выбран неверный статус, попробуй еще раз!)", reply_markup=gen_markup([x[0] for x in rows]))
            bot.register_next_step_handler(message, update_project_step_4, project_name=project_name, attribute=attribute)
            return
    user_id = message.from_user.id
    data = (update_info, project_name, user_id)
    manager.update_projects(attribute, data)
    bot.send_message(message.chat.id, "✅ Готово! Обновления внесены!)")

@bot.message_handler(func=lambda message: True)
def text_handler(message):
    """Обработка текстовых сообщений (поиск проекта по имени)"""
    user_id = message.from_user.id
    projects =[ x[2] for x in manager.get_projects(user_id)]
    project = message.text
    if project in projects:
        info_project(message, user_id, project)
        return
    bot.reply_to(message, "❓ Тебе нужна помощь?")
    info(message)

if __name__ == '__main__':
    bot.infinity_polling()