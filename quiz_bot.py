from telebot import types
import os
import telebot
from quiz_questions import questions
from collections import Counter
import json
import os.path


API_KEY = os.getenv("API_KEY")
bot = telebot.TeleBot(API_KEY, parse_mode=None)
data_file_name = "quiz_data.json"


def load_data():
    with open(data_file_name, "r") as file:
        json_data = json.load(file)
        return json_data


def save_data(data):
    with open(data_file_name, "w") as file:
        json.dump(data, file)


check_file = os.path.isfile(data_file_name)
data = None
if check_file:
    data = load_data()
else:
    data = {}


@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in data.keys():
        user_name = message.from_user.first_name
        bot.send_message(message.chat.id,
                         f"Hello, {user_name}. Before we starting you need to register by /register command.")
    else:
        bot.send_message(message.chat.id, "You can start quiz by /quiz")


@bot.message_handler(commands=['my_results'])
def check_results(message):
    user_id = message.from_user.id
    if user_id in data and "quiz_points" in data[user_id]:
        user_points = data[user_id]["quiz_points"]
        results_message = "Your results:\n"
        for topic, points in user_points.items():
            results_message += f"{topic}: {points} points\n"
        bot.send_message(message.chat.id, results_message)
    else:
        bot.send_message(message.chat.id, "You haven't taken any quiz yet.")


@bot.message_handler(commands=['quiz'])
def start_quiz(message):
    user_id = message.from_user.id
    if user_id in data.keys():
        markup = types.InlineKeyboardMarkup()
        for topic in questions:
            quiz_topic = topic["topic"]
            btn = types.InlineKeyboardButton(text=quiz_topic,
                                             callback_data=f'quiz_{quiz_topic}')
            markup.add(btn)
        bot.send_message(message.chat.id, "Choose quiz topic:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "For passing quiz you need to register by /register command!")


@bot.callback_query_handler(func=lambda call: call.data.startswith('quiz_'))
def select_quiz_topic(call):
    chat_id = call.message.chat.id
    topic = call.data.split("_")[1]
    send_question(chat_id, 0, topic)


def send_question(chat_id, question_index: int, topic):
    topic_questions = None
    for topic_id in questions:
        if topic_id["topic"] == topic:
            topic_questions = topic_id["questions"]
    if question_index < len(topic_questions):
        question = topic_questions[question_index]
        question_str = question["question"]
        correct_answer = question["correct_answer"]
        option_1 = question["options"]["A"]
        option_2 = question["options"]["B"]
        option_3 = question["options"]["C"]
        option_4 = question["options"]["D"]

        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text=option_1,
                                          callback_data=f'answer_{question_index}_A_{correct_answer}_{topic}')
        btn2 = types.InlineKeyboardButton(text=option_2,
                                          callback_data=f'answer_{question_index}_B_{correct_answer}_{topic}')
        btn3 = types.InlineKeyboardButton(text=option_3,
                                          callback_data=f'answer_{question_index}_C_{correct_answer}_{topic}')
        btn4 = types.InlineKeyboardButton(text=option_4,
                                          callback_data=f'answer_{question_index}_D_{correct_answer}_{topic}')
        markup.add(btn1, btn2, btn3, btn4, row_width=2)
        bot.send_message(chat_id, question_str, reply_markup=markup)
    else:
        bot.send_message(chat_id, f"Quiz completed! 🎉")


@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_'))
def check_answer(call):
    right_answer = call.data.split("_")[3]
    user_choice = call.data.split("_")[2]
    question_index = int(call.data.split("_")[1])
    topic = call.data.split("_")[4]
    user_id = call.from_user.id

    if user_choice == right_answer:
        bot.send_message(call.message.chat.id, "Correct! 🎉")
        add_point(user_id, topic)
    else:
        bot.send_message(call.message.chat.id, "Incorrect! 😔")

    send_question(call.message.chat.id, question_index + 1, topic)


def add_point(user_id, topic):
    if topic not in data[user_id]["quiz_points"]:
        data[user_id]["quiz_points"][topic] = 0

    data[user_id]["quiz_points"][topic] += 1
    save_data(data)


@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    if user_id in data.keys():
        bot.send_message(message.chat.id, f"You already registered!")
    else:
        data[user_id] = {
            "name": user_name,
            "quiz_points": {}  # Ініціалізуємо порожній словник для підрахунку балів
        }
        save_data(data)
        bot.send_message(message.chat.id, f"How old are you? Or type 'exit' to pass this step.")
        bot.register_next_step_handler(message, ask_age)


@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    user_points = {}
    for user_id, user_data in data.items():
        total_points = sum(user_data.get("quiz_points", {}).values())
        user_name = user_data["name"]
        user_points[user_name] = total_points

    sorted_leaderboard = Counter(user_points).most_common(5)

    leaderboard_message = "🏆 Top 5 Players: \n"
    for position, (name, points) in enumerate(sorted_leaderboard, start=1):
        leaderboard_message += f"{position}. {name}: {points} points\n"

    bot.send_message(message.chat.id, leaderboard_message)


def ask_age(message):
    if message.text.lower() == "exit":
        return
    user_id = message.from_user.id
    try:
        age = int(message.text)
        data[user_id]["age"] = age
        save_data(data)
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number of age, or 'exit' to pass this step.")
        bot.register_next_step_handler(message, ask_age)
    else:
        bot.send_message(message.chat.id, f"Thank you for register. Your name: {data[user_id]['name']}, "
                                          f"age: {data[user_id]['age']}")


bot.infinity_polling()
