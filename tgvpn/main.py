import logging
import telebot
from telebot import types
import requests
import time
from flask import Flask, request, jsonify

# 🔹 Конфигурация бота и Nicepay
TOKEN = "6871662291:AAHuf-HbqL6FNRYfgri05Zy870KR6xSIIo"
NICEPAY_API_URL = "https://nicepay.io/public/api/payment"
NICEPAY_API_KEY = "UfdhS-UifN8-HwJsj-kgo1G-dlKsp"
MERCHANT_ID = "67d06e3b76a1d36c654e659b"
SECRET_KEY = "UfdhS-UifN8-HwJsj-kgo1G-dlKsp"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# 🔹 Список тарифов VPN
vpn_plans = {
    "1 месяц - 250 ₽": {"id": "vpn_1m", "price": 250},
    "3 месяца - 1200 ₽": {"id": "vpn_3m", "price": 1200},
    "6 месяцев - 2000 ₽": {"id": "vpn_6m", "price": 2000}
}

orders = {}


# 🔹 Создание клавиатуры тарифов
def get_vpn_keyboard():
    markup = types.InlineKeyboardMarkup()
    for plan, data in vpn_plans.items():
        markup.add(types.InlineKeyboardButton(text=plan, callback_data=data["id"]))
    return markup


@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.send_message(message.chat.id, "👋 Привет! Выберите тариф VPN:", reply_markup=get_vpn_keyboard())


# 🔹 Обработка выбора тарифа
@bot.callback_query_handler(func=lambda call: call.data in [p["id"] for p in vpn_plans.values()])
def choose_payment_method(call):
    selected_plan = next((plan for plan, data in vpn_plans.items() if data["id"] == call.data), None)

    if not selected_plan:
        bot.send_message(call.message.chat.id, "❌ Ошибка! Тариф не найден.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Оплатить картой/СБП", callback_data=f"bank_rf_{call.data}"))
    markup.add(types.InlineKeyboardButton(text="Оплатить через NicePay", callback_data=f"nicepay_{call.data}"))

    bot.send_message(call.message.chat.id, f"💳 Вы выбрали: {selected_plan}\nВыберите способ оплаты:",
                     reply_markup=markup)


# 🔹 Функция создания платежа через банк РФ
def create_bank_payment(chat_id, amount):
    order_id = f"vpn_{chat_id}_{int(time.time())}"
    orders[order_id] = chat_id

    headers = {"Authorization": f"Bearer {NICEPAY_API_KEY}", "Content-Type": "application/json"}
    payment_data = {
        "merchant_id": MERCHANT_ID,
        "secret": SECRET_KEY,
        "order_id": order_id,
        "amount": amount * 100,
        "currency": "RUB",
        "description": "Оплата VPN",
        "payment_method": "bank",
        "callback_url": "https://ВАШ_СЕРВЕР/nicepay_webhook",
        "customer": {"email": f"user{chat_id}@vpn.com", "phone": "79920512436", "name": f"User {chat_id}"}
    }

    response = requests.post(NICEPAY_API_URL, headers=headers, json=payment_data)
    json_resp = response.json()
    payment_link = json_resp.get("data", {}).get("link")

    if payment_link:
        bot.send_message(chat_id, f"💳 Оплатите по ссылке: [Оплатить]({payment_link})", parse_mode="MarkdownV2")
    else:
        bot.send_message(chat_id, "❌ Ошибка при создании платежа.")


# 🔹 Функция создания платежа через NicePay
def create_nicepay_payment(chat_id, amount):
    order_id = f"vpn_{chat_id}_{int(time.time())}"
    orders[order_id] = chat_id

    headers = {"Authorization": f"Bearer {NICEPAY_API_KEY}", "Content-Type": "application/json"}
    payment_data = {
        "merchant_id": MERCHANT_ID,
        "secret": SECRET_KEY,
        "order_id": order_id,
        "amount": amount * 100,
        "currency": "RUB",
        "description": "Оплата VPN",
        "callback_url": "https://ВАШ_СЕРВЕР/nicepay_webhook",
        "customer": {"email": f"user{chat_id}@vpn.com", "phone": "79920512436", "name": f"User {chat_id}"}
    }

    response = requests.post(NICEPAY_API_URL, headers=headers, json=payment_data)
    json_resp = response.json()
    payment_link = json_resp.get("data", {}).get("link")

    if payment_link:
        bot.send_message(chat_id, f"💳 Оплатите по ссылке: [Оплатить]({payment_link})", parse_mode="MarkdownV2")
    else:
        bot.send_message(chat_id, "❌ Ошибка при создании платежа.")


# 🔹 Обработка оплаты через банк РФ
@bot.callback_query_handler(func=lambda call: call.data.startswith("bank_rf_"))
def pay_by_bank(call):
    plan_id = call.data.split("_")[2]
    plan = next((p for p in vpn_plans.values() if p["id"] == plan_id), None)

    if not plan:
        bot.send_message(call.message.chat.id, "❌ Ошибка! Тариф не найден.")
        return

    create_bank_payment(call.message.chat.id, plan["price"])


# 🔹 Обработка оплаты через NicePay
@bot.callback_query_handler(func=lambda call: call.data.startswith("nicepay_"))
def pay_by_nicepay(call):
    plan_id = call.data.split("_")[1]
    plan = next((p for p in vpn_plans.values() if p["id"] == plan_id), None)

    if not plan:
        bot.send_message(call.message.chat.id, "❌ Ошибка! Тариф не найден.")
        return

    create_nicepay_payment(call.message.chat.id, plan["price"])


# 🔹 Запуск бота
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.polling(none_stop=True)

