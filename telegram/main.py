import os
import logging
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
)
from supabase import create_client, Client
import pytz
import time
from aiolimiter import AsyncLimiter

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ID_MAPPING_FILE = "id_mapping.json"
TIMER_FILE = "timer.json"

# Validate environment variables
if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables: TELEGRAM_TOKEN, SUPABASE_URL, or SUPABASE_KEY")

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SUPABASE CLIENT ---
def init_supabase():
    """Initialize Supabase client with retry logic."""
    retries = 3
    for attempt in range(retries):
        try:
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Successfully connected to Supabase.")
            return client
        except Exception as e:
            logger.error(f"Supabase connection attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    logger.error("Failed to connect to Supabase after retries.")
    return None

supabase: Client = init_supabase()
rate_limiter = AsyncLimiter(20, 1)  # 20 req/s

# --- CONVERSATION STATES ---
GET_USER_ID_DATA, CHOOSE_TABLE, CHOOSE_ACTION, CHOOSE_RECORDS_LATEST, GET_FILTER_VALUE = range(5)
GET_USER_ID_TIMER, GET_MINUTES, CHOOSE_REPEAT, CHOOSE_TABLE_TIMER, CHOOSE_ACTION_TIMER, CHOOSE_RECORDS_LATEST_TIMER, GET_FILTER_VALUE_TIMER = range(5, 12)

# --- HELPER FUNCTIONS ---
def load_json_file(filename: str):
    """Loads a JSON file."""
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_json_file(filename: str, data: dict):
    """Saves data to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logger.error(f"Could not save {filename}: {e}")

def load_id_mapping():
    return load_json_file(ID_MAPPING_FILE)

def save_id_mapping(telegram_id: int, profile_id: str):
    mapping = load_id_mapping()
    mapping[str(telegram_id)] = profile_id
    save_json_file(ID_MAPPING_FILE, mapping)

def clear_id_mapping(telegram_id: int):
    mapping = load_id_mapping()
    if str(telegram_id) in mapping:
        del mapping[str(telegram_id)]
        save_json_file(ID_MAPPING_FILE, mapping)
        return True
    return False

async def get_user_profile_by_id(user_id: str):
    """Fetches a user's profile from Supabase using their profile ID."""
    if not supabase:
        return None, "Supabase connection not available."
    try:
        query = supabase.table("user_profiles").select("*").eq("id", user_id).single()
        response = query.execute()
        profile = response.data
        if profile and not profile.get('timezone'):
            profile['timezone'] = 'Asia/Ho_Chi_Minh'  # Default
        return profile, None
    except Exception as e:
        if "PGRST116" in str(e):
            return None, None
        logger.error(f"Error fetching user profile for id {user_id}: {e}")
        return None, "An error occurred while fetching your profile."

# --- DATA FETCHING AND FORMATTING HELPERS ---
def _format_record(record: dict, table_name: str, timezone: str = 'Asia/Ho_Chi_Minh') -> str:
    """Formats a single record into a human-readable string."""
    if not record:
        return "No data available."

    tz = pytz.timezone(timezone)
    if table_name == "onetest":
        date_str = record.get("date", "N/A")
        try:
            dt_object = datetime.fromisoformat(date_str.replace('Z', '+00:00')).astimezone(tz)
            formatted_date = dt_object.strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = date_str
        bpm = record.get("bpm_avg", "N/A")
        temp = record.get("temperature", "N/A")
        return f"Date: {formatted_date}\nBPM: {bpm}\nTemperature: {temp}°C"
    elif table_name == "followhour":
        time_str = record.get("time", "N/A")
        try:
            dt_object = datetime.fromisoformat(time_str.replace('Z', '+00:00')).astimezone(tz)
            formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted_time = time_str
        bpm = record.get("bpm_avg", "N/A")
        temp = record.get("temperature", "N/A")
        return f"Time: {formatted_time}\nBPM: {bpm}\nTemperature: {temp}°C"
    return "Unknown table format."

async def _fetch_data_from_supabase(table_name: str, limit: int = None, filter_field: str = None, filter_value: str = None):
    """Generic function to fetch data from Supabase with optional limits and filters."""
    if not supabase:
        return None, "Supabase connection not available."

    async with rate_limiter:
        try:
            query = supabase.table(table_name).select("*")

            # Ordering
            if table_name == "onetest":
                query = query.order("date", desc=True)
            elif table_name == "followhour":
                query = query.order("time", desc=True)
            else:
                query = query.order("created_at", desc=True)

            # Filtering
            if filter_field and filter_value:
                if filter_field == "date":
                    try:
                        datetime.strptime(filter_value, '%Y-%m-%d')
                        start_of_day = f"{filter_value}T00:00:00+00:00"
                        end_of_day = f"{filter_value}T23:59:59+00:00"
                        query = query.gte("time", start_of_day).lte("time", end_of_day)
                    except ValueError:
                        return None, "Invalid date format. Please use YYYY-MM-DD."
                elif filter_field in ["bpm_avg", "temperature"]:
                    try:
                        low, high = map(float, filter_value.split('-'))
                        query = query.gte(filter_field, low).lte(filter_field, high)
                    except ValueError:
                        return None, "Invalid range format for filter."
                else:
                    query = query.eq(filter_field, filter_value)

            # Limiting
            if limit:
                query = query.limit(limit)

            response = query.execute()
            return response.data, None
        except Exception as e:
            if "PGRST116" in str(e):
                return [], None
            logger.error(f"Error fetching data from {table_name}: {e}")
            return None, "An error occurred while fetching data."

async def show_last_record(update: Update, context: CallbackContext) -> int:
    """Fetches and displays the last record from the chosen table."""
    table_choice = context.user_data.get('table_choice')
    profile = context.user_data.get('profile', {})
    timezone = profile.get('timezone', 'Asia/Ho_Chi_Minh')

    if not table_choice:
        await (update.callback_query or update.message).reply_text("Error: Table choice not found. Please restart with /data.")
        return ConversationHandler.END

    data, error_msg = await _fetch_data_from_supabase(table_choice, limit=1)

    if error_msg:
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    elif data:
        record_text = _format_record(data[0], table_choice, timezone)
        if update.callback_query:
            await update.callback_query.edit_message_text(f"Last record from {table_choice}:\n{record_text}")
        else:
            await update.message.reply_text(f"Last record from {table_choice}:\n{record_text}")
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text(f"No records found in {table_choice}.")
        else:
            await update.message.reply_text(f"No records found in {table_choice}.")

    keys_to_clear = ['table_choice', 'limit', 'filter_field', 'filter_value']
    for key in keys_to_clear:
        context.user_data.pop(key, None)
    return ConversationHandler.END

async def show_latest_records(update: Update, context: CallbackContext) -> int:
    """Fetches and displays the latest N records from the chosen table."""
    table_choice = context.user_data.get('table_choice')
    limit = context.user_data.get('limit')
    profile = context.user_data.get('profile', {})
    timezone = profile.get('timezone', 'Asia/Ho_Chi_Minh')

    if not table_choice or not limit:
        await (update.callback_query or update.message).reply_text("Error: Table or limit not found. Please restart with /data.")
        return ConversationHandler.END

    data, error_msg = await _fetch_data_from_supabase(table_choice, limit=limit)

    if error_msg:
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    elif data:
        response_text = f"Latest {len(data)} records from {table_choice}:\n\n"
        for record in data:
            response_text += _format_record(record, table_name=table_choice, timezone=timezone) + "\n---\n"
        if update.callback_query:
            await update.callback_query.edit_message_text(response_text)
        else:
            await update.message.reply_text(response_text)
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text(f"No records found in {table_choice}.")
        else:
            await update.message.reply_text(f"No records found in {table_choice}.")

    keys_to_clear = ['table_choice', 'limit', 'filter_field', 'filter_value']
    for key in keys_to_clear:
        context.user_data.pop(key, None)
    return ConversationHandler.END

async def received_filter_value(update: Update, context: CallbackContext) -> int:
    """Handles the filter value input and fetches/displays filtered records."""
    filter_value = update.message.text
    table_choice = context.user_data.get('table_choice')
    filter_field = context.user_data.get('filter_field')
    profile = context.user_data.get('profile', {})
    timezone = profile.get('timezone', 'Asia/Ho_Chi_Minh')

    if not table_choice or not filter_field:
        await update.message.reply_text("Error: Missing context for filtering. Please restart with /data.")
        return ConversationHandler.END

    if filter_field in ['bpm_avg', 'temperature']:
        try:
            low, high = map(float, filter_value.split('-'))
            if low > high:
                await update.message.reply_text("Invalid range: low value cannot be greater than high value. Please re-enter (e.g., 60-90).")
                return GET_FILTER_VALUE
            parsed_filter_value = f"{low}-{high}"
        except ValueError:
            await update.message.reply_text("Invalid range format. Please use the format 'low-high' (e.g., 60-90).")
            return GET_FILTER_VALUE
    elif filter_field == 'date':
        try:
            datetime.strptime(filter_value, '%Y-%m-%d')
            parsed_filter_value = filter_value
        except ValueError:
            await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD (e.g., 2023-01-15).")
            return GET_FILTER_VALUE
    else:
        parsed_filter_value = filter_value

    data, error_msg = await _fetch_data_from_supabase(table_choice, filter_field=filter_field, filter_value=parsed_filter_value)

    if error_msg:
        await update.message.reply_text(error_msg)
    elif data:
        response_text = f"Records from {table_choice} filtered by {filter_field.replace('_', ' ')} '{filter_value}':\n\n"
        for record in data:
            response_text += _format_record(record, table_name=table_choice, timezone=timezone) + "\n---\n"
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text(f"No records found in {table_choice} for the given filter.")

    keys_to_clear = ['table_choice', 'limit', 'filter_field', 'filter_value']
    for key in keys_to_clear:
        context.user_data.pop(key, None)
    return ConversationHandler.END

# --- TIMER FUNCTIONS ---
def load_timer_file():
    return load_json_file(TIMER_FILE)

def save_timer_file(data: dict):
    save_json_file(TIMER_FILE, data)

def save_timer(chat_id: int, timer_data: dict):
    timers = load_timer_file()
    timers[str(chat_id)] = timer_data
    save_timer_file(timers)

def clear_timer_json(chat_id: int) -> bool:
    timers = load_timer_file()
    chat_id_str = str(chat_id)
    if chat_id_str in timers:
        del timers[chat_id_str]
        save_timer_file(timers)
        return True
    return False

def calculate_first(now: float, first_due: float, interval: float) -> float:
    if now < first_due:
        return first_due - now
    else:
        elapsed = now - first_due
        remainder = elapsed % interval
        if remainder == 0:
            return 0
        else:
            return interval - remainder

def load_timers(job_queue):
    timers = load_timer_file()
    now = time.time()
    for chat_id_str in list(timers.keys()):
        timer = timers[chat_id_str]
        t_type = timer.get('type')
        config = timer['config'].copy()
        config['timer_type'] = t_type
        if t_type == 'one-time':
            due_time = timer.get('due_time')
            if due_time is None or due_time <= now:
                del timers[chat_id_str]
                continue
            seconds = due_time - now
            job_queue.run_once(timer_callback, seconds, chat_id=int(chat_id_str), name=f"timer_{chat_id_str}", data=config)
        elif t_type == 'repeating':
            interval = timer.get('interval')
            first_due = timer.get('first_due')
            if interval is None or first_due is None:
                del timers[chat_id_str]
                continue
            first = calculate_first(now, first_due, interval)
            job_queue.run_repeating(timer_callback, interval, first=first, chat_id=int(chat_id_str), name=f"timer_{chat_id_str}", data=config)
    save_timer_file(timers)

async def timer_callback(context: CallbackContext):
    job = context.job
    chat_id = job.chat_id
    config = job.data
    id_mapping = load_id_mapping()
    profile_id = id_mapping.get(str(chat_id))
    if not profile_id:
        await context.bot.send_message(chat_id, "No profile found. Please login with /data first.")
        if config.get('timer_type') == 'one-time':
            clear_timer_json(chat_id)
        return
    profile, error = await get_user_profile_by_id(profile_id)
    if error or not profile:
        await context.bot.send_message(chat_id, "Error fetching profile.")
        if config.get('timer_type') == 'one-time':
            clear_timer_json(chat_id)
        return
    timezone = profile.get('timezone', 'Asia/Ho_Chi_Minh')
    table = config['table']
    mode = config['mode']
    if mode == 'last':
        data, error_msg = await _fetch_data_from_supabase(table, limit=1)
        if error_msg:
            await context.bot.send_message(chat_id, error_msg)
            if config.get('timer_type') == 'one-time':
                clear_timer_json(chat_id)
            return
        if data:
            record_text = _format_record(data[0], table, timezone)
            await context.bot.send_message(chat_id, f"Timer triggered! Last record from {table}:\n{record_text}")
        else:
            await context.bot.send_message(chat_id, f"No records found in {table}.")
    elif mode == 'latest':
        limit = config['limit']
        data, error_msg = await _fetch_data_from_supabase(table, limit=limit)
        if error_msg:
            await context.bot.send_message(chat_id, error_msg)
            if config.get('timer_type') == 'one-time':
                clear_timer_json(chat_id)
            return
        if data:
            response_text = f"Timer triggered! Latest {len(data)} records from {table}:\n\n"
            for record in data:
                response_text += _format_record(record, table_name=table, timezone=timezone) + "\n---\n"
            await context.bot.send_message(chat_id, response_text)
        else:
            await context.bot.send_message(chat_id, f"No records found in {table}.")
    elif mode == 'filter':
        filter_field = config['filter_field']
        filter_value = config['filter_value']
        data, error_msg = await _fetch_data_from_supabase(table, filter_field=filter_field, filter_value=filter_value)
        if error_msg:
            await context.bot.send_message(chat_id, error_msg)
            if config.get('timer_type') == 'one-time':
                clear_timer_json(chat_id)
            return
        if data:
            response_text = f"Timer triggered! Records from {table} filtered by {filter_field.replace('_', ' ')} '{filter_value}':\n\n"
            for record in data:
                response_text += _format_record(record, table_name=table, timezone=timezone) + "\n---\n"
            await context.bot.send_message(chat_id, response_text)
        else:
            await context.bot.send_message(chat_id, f"No records found in {table} for the given filter.")
    if config.get('timer_type') == 'one-time':
        clear_timer_json(chat_id)

async def clear_timer(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(f"timer_{chat_id}")
    removed = False
    for job in current_jobs:
        job.schedule_removal()
        removed = True
    json_removed = clear_timer_json(chat_id)
    if removed or json_removed:
        await update.message.reply_text("Timer cleared.")
    else:
        await update.message.reply_text("No timer set.")

async def do_schedule(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(f"timer_{chat_id}")
    for job in current_jobs:
        job.schedule_removal()
    clear_timer_json(chat_id)
    mode = context.user_data['mode']
    table_choice = context.user_data['table_choice']
    config = {'mode': mode, 'table': table_choice, 'timer_type': context.user_data['timer_type']}
    if mode == 'latest':
        config['limit'] = context.user_data['limit']
    elif mode == 'filter':
        config['filter_field'] = context.user_data['filter_field']
        config['filter_value'] = context.user_data['filter_value']
    minutes = context.user_data['minutes']
    interval = minutes * 60
    set_time = time.time()
    timer_type = context.user_data['timer_type']
    if timer_type == 'one-time':
        due_time = set_time + interval
        context.job_queue.run_once(timer_callback, interval, chat_id=chat_id, name=f"timer_{chat_id}", data=config)
        save_timer(chat_id, {'type': 'one-time', 'due_time': due_time, 'config': config})
        await update.message.reply_text(f"One-time timer set for {minutes} minutes to fetch {table_choice} data.")
    else:  # repeating
        first_due = set_time + interval
        context.job_queue.run_repeating(timer_callback, interval, first=interval, chat_id=chat_id, name=f"timer_{chat_id}", data=config)
        save_timer(chat_id, {'type': 'repeating', 'first_due': first_due, 'interval': interval, 'config': config})
        await update.message.reply_text(f"Repeating timer set every {minutes} minutes to fetch {table_choice} data.")
    keys_to_clear = ['minutes', 'timer_type', 'table_choice', 'mode', 'limit', 'filter_field', 'filter_value', 'profile']
    for key in keys_to_clear:
        context.user_data.pop(key, None)
    return ConversationHandler.END

# --- TIMER CONVERSATION HANDLERS ---
async def settimer_start(update: Update, context: CallbackContext) -> int:
    telegram_id = update.effective_user.id
    id_mapping = load_id_mapping()
    cached_profile_id = id_mapping.get(str(telegram_id))
    if cached_profile_id:
        profile, error_msg = await get_user_profile_by_id(cached_profile_id)
        if profile:
            context.user_data['profile'] = profile
            status = profile.get("status")
            if status != "approved":
                message = "Your account access was not approved." if status == "rejected" else "Your account is still waiting for admin approval."
                await update.message.reply_text(message)
                return ConversationHandler.END
            await update.message.reply_text("Please enter the number of minutes for the timer.")
            return GET_MINUTES
        else:
            logger.warning(f"Stale cached profile ID {cached_profile_id} for telegram_id {telegram_id}. Clearing.")
            clear_id_mapping(telegram_id)
    await update.message.reply_text("Please enter your user ID to continue.")
    return GET_USER_ID_TIMER

async def received_user_id_timer(update: Update, context: CallbackContext) -> int:
    user_id = update.message.text
    telegram_id = update.effective_user.id
    profile, error_msg = await get_user_profile_by_id(user_id)
    if error_msg:
        await update.message.reply_text(error_msg)
        return ConversationHandler.END
    if not profile:
        await update.message.reply_text("This ID is not registered. Please contact an administrator.")
        return ConversationHandler.END
    status = profile.get("status")
    if status != "approved":
        message = "Your account access was not approved." if status == "rejected" else "Your account is still waiting for admin approval."
        await update.message.reply_text(message)
        return ConversationHandler.END
    save_id_mapping(telegram_id, profile['id'])
    context.user_data['profile'] = profile
    await update.message.reply_text("Please enter the number of minutes for the timer.")
    return GET_MINUTES

async def received_minutes(update: Update, context: CallbackContext) -> int:
    try:
        minutes = int(update.message.text)
        if minutes <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return GET_MINUTES
        context.user_data['minutes'] = minutes
        keyboard = [
            [InlineKeyboardButton("One-time", callback_data='one-time')],
            [InlineKeyboardButton("Repeating", callback_data='repeating')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose timer type:", reply_markup=reply_markup)
        return CHOOSE_REPEAT
    except ValueError:
        await update.message.reply_text("That doesn't look like a valid number. Please enter a number.")
        return GET_MINUTES

async def choose_repeat(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    timer_type = query.data
    context.user_data['timer_type'] = timer_type
    await query.edit_message_text(f"Timer type set to {timer_type}.")
    return await prompt_table_choice_timer(update, context)

async def prompt_table_choice_timer(update: Update, context: CallbackContext) -> int:
    profile = context.user_data.get('profile')
    if not profile:
        await update.message.reply_text("Something went wrong. Please start over with /settimer.")
        return ConversationHandler.END
    email = profile.get("email", "user")
    keyboard = [
        [InlineKeyboardButton("Real-time Data (followhour)", callback_data='followhour')],
        [InlineKeyboardButton("Daily Test Data (onetest)", callback_data='onetest')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = f"Which data would you like to view after the timer?"
    if update.callback_query:
        await update.callback_query.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    return CHOOSE_TABLE_TIMER

async def choose_table_timer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    table = query.data
    context.user_data['table_choice'] = table
    if table == 'onetest':
        keyboard = [
            [InlineKeyboardButton("View Last Record", callback_data='view_last')],
            [InlineKeyboardButton("Filter by BPM Range", callback_data='filter_bpm_avg')],
            [InlineKeyboardButton("Filter by Temperature Range", callback_data='filter_temperature')],
        ]
    else:  # followhour
        keyboard = [
            [InlineKeyboardButton("View Latest Records", callback_data='view_latest')],
            [InlineKeyboardButton("Filter by Date", callback_data='filter_date')],
            [InlineKeyboardButton("Filter by BPM Range", callback_data='filter_bpm_avg')],
            [InlineKeyboardButton("Filter by Temperature Range", callback_data='filter_temperature')],
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="What would you like to do?", reply_markup=reply_markup)
    return CHOOSE_ACTION_TIMER

async def choose_action_timer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    if action == 'view_last':
        context.user_data['mode'] = 'last'
        await query.edit_message_text(text="Timer will fetch the last record.")
        return await do_schedule(update, context)
    if action == 'view_latest':
        context.user_data['mode'] = 'latest'
        await query.edit_message_text(text="Please enter the number of latest records you would like to see (e.g., 10).")
        return CHOOSE_RECORDS_LATEST_TIMER
    elif action.startswith('filter_'):
        context.user_data['mode'] = 'filter'
        filter_field = action.split('_', 1)[1]
        context.user_data['filter_field'] = filter_field
        prompt = f"Please enter the value for {filter_field.replace('_', ' ')}:"
        if filter_field == 'date':
            prompt += " (e.g., YYYY-MM-DD)"
        elif filter_field in ['bpm_avg', 'temperature']:
            prompt = f"Please enter the range for {filter_field.replace('_', ' ')} (e.g., 60-90)."
        await query.edit_message_text(text=prompt)
        return GET_FILTER_VALUE_TIMER

async def choose_records_latest_input_timer(update: Update, context: CallbackContext) -> int:
    try:
        limit = int(update.message.text)
        if limit <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return CHOOSE_RECORDS_LATEST_TIMER
        context.user_data['limit'] = limit
        return await do_schedule(update, context)
    except ValueError:
        await update.message.reply_text("That doesn't look like a valid number. Please enter a number.")
        return CHOOSE_RECORDS_LATEST_TIMER

async def received_filter_value_timer(update: Update, context: CallbackContext) -> int:
    filter_value = update.message.text
    filter_field = context.user_data.get('filter_field')
    if not filter_field:
        await update.message.reply_text("Error: Missing context for filtering. Please restart with /settimer.")
        return ConversationHandler.END
    if filter_field in ['bpm_avg', 'temperature']:
        try:
            low, high = map(float, filter_value.split('-'))
            if low > high:
                await update.message.reply_text("Invalid range: low value cannot be greater than high value. Please re-enter (e.g., 60-90).")
                return GET_FILTER_VALUE_TIMER
            parsed_filter_value = f"{low}-{high}"
        except ValueError:
            await update.message.reply_text("Invalid range format. Please use the format 'low-high' (e.g., 60-90).")
            return GET_FILTER_VALUE_TIMER
    elif filter_field == 'date':
        try:
            datetime.strptime(filter_value, '%Y-%m-%d')
            parsed_filter_value = filter_value
        except ValueError:
            await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD (e.g., 2023-01-15).")
            return GET_FILTER_VALUE_TIMER
    else:
        parsed_filter_value = filter_value
    context.user_data['filter_value'] = parsed_filter_value
    return await do_schedule(update, context)

# --- COMMAND HANDLERS ---
async def start_command(update: Update, context: CallbackContext):
    """Displays a help message with available commands."""
    help_text = (
        "Welcome to the Health Monitoring Bot! Here are the available commands:\n\n"
        "• /start or /help: Show this help message.\n"
        "• /data: Begin the process to view your health data.\n"
        "• /settimer: Set a one-time or repeating timer to receive data after/every specified minutes.\n"
        "• /cleartimer: Clear the set timer.\n"
        "• /logout: Clear your saved login information."
    )
    await update.message.reply_text(help_text)

async def help_command(update: Update, context: CallbackContext):
    """Displays a help message with available commands."""
    await start_command(update, context)

async def logout_command(update: Update, context: CallbackContext):
    """Logs the user out by clearing their cached ID."""
    telegram_id = update.effective_user.id
    logged_out = clear_id_mapping(telegram_id)

    if logged_out:
        context.user_data.clear()
        await update.message.reply_text("You have been successfully logged out.")
    else:
        await update.message.reply_text("You were not logged in.")

# --- DATA CONVERSATION HANDLERS ---
async def data_start(update: Update, context: CallbackContext) -> int:
    """Entry point for the /data conversation. Checks for cached ID or asks for it."""
    telegram_id = update.effective_user.id
    id_mapping = load_id_mapping()
    cached_profile_id = id_mapping.get(str(telegram_id))

    if cached_profile_id:
        profile, error_msg = await get_user_profile_by_id(cached_profile_id)
        if profile:
            context.user_data['profile'] = profile
            return await prompt_table_choice(update, context)
        else:
            logger.warning(f"Stale cached profile ID {cached_profile_id} for telegram_id {telegram_id}. Clearing.")
            clear_id_mapping(telegram_id)

    await update.message.reply_text("Please enter your user ID to continue.")
    return GET_USER_ID_DATA

async def received_user_id_data(update: Update, context: CallbackContext) -> int:
    """Handles the user ID entered during the /data flow."""
    user_id = update.message.text
    telegram_id = update.effective_user.id
    profile, error_msg = await get_user_profile_by_id(user_id)

    if error_msg:
        await update.message.reply_text(error_msg)
        return ConversationHandler.END
    if not profile:
        await update.message.reply_text("This ID is not registered. Please contact an administrator.")
        return ConversationHandler.END

    save_id_mapping(telegram_id, profile['id'])
    context.user_data['profile'] = profile
    return await prompt_table_choice(update, context)

async def prompt_table_choice(update: Update, context: CallbackContext) -> int:
    """Shows the table selection menu to the user."""
    profile = context.user_data.get('profile')
    if not profile:
        await update.message.reply_text("Something went wrong. Please start over with /data.")
        return ConversationHandler.END

    status = profile.get("status")
    if status != "approved":
        message = "Your account access was not approved." if status == "rejected" else "Your account is still waiting for admin approval."
        if update.callback_query:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return ConversationHandler.END

    email = profile.get("email", "user")
    keyboard = [
        [InlineKeyboardButton("Real-time Data (followhour)", callback_data='followhour')],
        [InlineKeyboardButton("Daily Test Data (onetest)", callback_data='onetest')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = f"Welcome back, {email}. Which data would you like to view?"
    if update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

    return CHOOSE_TABLE

async def choose_table(update: Update, context: CallbackContext) -> int:
    """Stores the chosen table and asks for the next action based on the table."""
    query = update.callback_query
    await query.answer()
    table = query.data
    context.user_data['table_choice'] = table

    if table == 'onetest':
        keyboard = [
            [InlineKeyboardButton("View Last Record", callback_data='view_last')],
            [InlineKeyboardButton("Filter by BPM Range", callback_data='filter_bpm_avg')],
            [InlineKeyboardButton("Filter by Temperature Range", callback_data='filter_temperature')],
        ]
    else:  # followhour
        keyboard = [
            [InlineKeyboardButton("View Latest Records", callback_data='view_latest')],
            [InlineKeyboardButton("Filter by Date", callback_data='filter_date')],
            [InlineKeyboardButton("Filter by BPM Range", callback_data='filter_bpm_avg')],
            [InlineKeyboardButton("Filter by Temperature Range", callback_data='filter_temperature')],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="What would you like to do?", reply_markup=reply_markup)
    return CHOOSE_ACTION

async def choose_action(update: Update, context: CallbackContext) -> int:
    """Handles the user's choice of action (view latest, view last, or filter)."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'view_last':
        return await show_last_record(update, context)

    if action == 'view_latest':
        await query.edit_message_text(text="Please enter the number of latest records you would like to see (e.g., 10).")
        return CHOOSE_RECORDS_LATEST

    elif action.startswith('filter_'):
        filter_field = action.split('_', 1)[1]
        context.user_data['filter_field'] = filter_field

        prompt = f"Please enter the value for {filter_field.replace('_', ' ')}:"
        if filter_field == 'date':
            prompt += " (e.g., YYYY-MM-DD)"
        elif filter_field in ['bpm_avg', 'temperature']:
            prompt = f"Please enter the range for {filter_field.replace('_', ' ')} (e.g., 60-90)."

        await query.edit_message_text(text=prompt)
        return GET_FILTER_VALUE

async def choose_records_latest_input(update: Update, context: CallbackContext) -> int:
    """Handles the numerical input for the number of latest records."""
    try:
        limit = int(update.message.text)
        if limit <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return CHOOSE_RECORDS_LATEST
        context.user_data['limit'] = limit
        return await show_latest_records(update, context)
    except ValueError:
        await update.message.reply_text("That doesn't look like a valid number. Please enter a number.")
        return CHOOSE_RECORDS_LATEST

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}")
    if update and update.effective_chat:
        await update.effective_chat.send_message("An error occurred. Please try again or contact support.")

# --- MAIN FUNCTION ---
def main():
    """Starts the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    load_timers(application.job_queue)

    data_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("data", data_start)],
        states={
            GET_USER_ID_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_user_id_data)],
            CHOOSE_TABLE: [CallbackQueryHandler(choose_table)],
            CHOOSE_ACTION: [CallbackQueryHandler(choose_action)],
            CHOOSE_RECORDS_LATEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_records_latest_input)],
            GET_FILTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_filter_value)],
        },
        fallbacks=[CommandHandler("cancel", start_command)],
    )

    timer_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("settimer", settimer_start)],
        states={
            GET_USER_ID_TIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_user_id_timer)],
            GET_MINUTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_minutes)],
            CHOOSE_REPEAT: [CallbackQueryHandler(choose_repeat)],
            CHOOSE_TABLE_TIMER: [CallbackQueryHandler(choose_table_timer)],
            CHOOSE_ACTION_TIMER: [CallbackQueryHandler(choose_action_timer)],
            CHOOSE_RECORDS_LATEST_TIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_records_latest_input_timer)],
            GET_FILTER_VALUE_TIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_filter_value_timer)],
        },
        fallbacks=[CommandHandler("cancel", start_command)],
    )

    application.add_handler(data_conv_handler)
    application.add_handler(timer_conv_handler)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("cleartimer", clear_timer))

    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()