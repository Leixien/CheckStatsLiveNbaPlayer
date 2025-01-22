import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configura il logging
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = "7784704083:AAG54-OxBwaTXIuPiT40u1f2YBJoRSm-MZQ"

# Funzione per effettuare richieste API
def make_api_request(url, params=None):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Genera un'eccezione per errori HTTP
        # Prova a interpretare la risposta come JSON
        try:
            return response.json()
        except ValueError:
            return {"error": "Invalid JSON response from API."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

# Funzione per ottenere partite live
def get_live_games():
    API_URL = "https://www.balldontlie.io/api/v1/games"
    response = make_api_request(API_URL, params={"per_page": 10, "live": "true"})
    if "error" in response:
        return []
    return response.get("data", [])

# Funzione per ottenere statistiche live di un giocatore
def get_player_live_stats(player_name):
    API_URL = "https://www.balldontlie.io/api/v1/players"
    response = make_api_request(API_URL, {"search": player_name})

    if "error" in response:
        return response

    players = response.get("data", [])
    if not players:
        return {"error": "Player not found."}

    player = players[0]
    player_id = player.get("id")
    stats_url = f"https://www.balldontlie.io/api/v1/stats?player_ids[]={player_id}&per_page=1"
    stats_response = make_api_request(stats_url)

    if "error" in stats_response:
        return stats_response

    stats_data = stats_response.get("data", [])
    if stats_data:
        game_stats = stats_data[0]
        return {
            "name": player.get("first_name") + " " + player.get("last_name"),
            "team": player.get("team", {}).get("full_name"),
            "points": game_stats.get("pts"),
            "rebounds": game_stats.get("reb"),
            "assists": game_stats.get("ast"),
            "game_date": game_stats.get("game", {}).get("date"),
        }
    return {"error": "No live stats available for this player."}

# Helper function to split long messages
def split_message(text, max_length=4096):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# Command handler for /live
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    games = get_live_games()

    if not games:
        await update.message.reply_text("No live NBA games at the moment.")
        return

    keyboard = []
    for game in games:
        home_team = game["home_team"]["full_name"]
        visitor_team = game["visitor_team"]["full_name"]
        game_id = game["id"]

        keyboard.append([
            InlineKeyboardButton(f"{visitor_team} vs {home_team}", callback_data=f"game_{game_id}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a live game:", reply_markup=reply_markup)

# Callback handler for game selection
async def game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    game_id = query.data.split("_")[1]
    context.user_data["selected_game"] = game_id

    await query.edit_message_text("Game selected! Now use /player <name> to check player stats.")

# Command handler for /liveStats
async def live_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Please provide a player name. Usage: /liveStats <name>")
        return

    player_name = ' '.join(context.args)
    stats = get_player_live_stats(player_name)

    if "error" in stats:
        for chunk in split_message(stats["error"]):
            await update.message.reply_text(chunk)
    else:
        stats_message = (
            f"Player Stats:\n"
            f"Name: {stats['name']}\n"
            f"Team: {stats['team']}\n"
            f"Points: {stats['points']}\n"
            f"Rebounds: {stats['rebounds']}\n"
            f"Assists: {stats['assists']}\n"
            f"Game Date: {stats['game_date']}"
        )

        for chunk in split_message(stats_message):
            await update.message.reply_text(chunk)

# Main function to start the bot
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CallbackQueryHandler(game_selection, pattern="^game_"))
    application.add_handler(CommandHandler("liveStats", live_stats))

    application.run_polling()

if __name__ == "__main__":
    main()
