import random
import string
import re
import unicodedata
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message
from pytgcalls.exceptions import NoActiveGroupCall
import config
from PritiMusic import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app, LOGGER
from PritiMusic.core.call import Lucky
from PritiMusic.misc import SUDOERS
from PritiMusic.utils import seconds_to_min, time_to_seconds
from PritiMusic.utils.channelplay import get_channeplayCB
from PritiMusic.utils.decorators.language import languageCB
from PritiMusic.utils.decorators.play import PlayWrapper
from PritiMusic.utils.formatters import formats
from PritiMusic.utils.inline import botplaylist_markup, livestream_markup, playlist_markup, slider_markup, track_markup
from PritiMusic.utils.logger import play_logs
from PritiMusic.utils.stream.stream import stream
from config import BANNED_USERS, lyrical

BANNED_WORDS = ["porn", "pornhub", "xvideos", "xnxx", "brazzers", "onlyfans", "xhamster", "hot bhabhi", "deskbabe", "redtube", "spankbang", "child porn", "pedophile", "pedo", "jailbait", "loli", "shota", "csam", "incest", "bestiality", "zoophilia", "snuff", "revenge porn", "nonconsensual"]

def clean_invisible_chars(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKC', text)
    return re.sub(r'[\u200B-\u200D\uFEFF\u202A-\u202E\u200e\u200f]', '', text)

def is_nsfw_content(text):
    if not text: return False
    text = clean_invisible_chars(str(text).lower())
    for word in BANNED_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', text): return True
    return False

def is_malicious_link(text):
    if not text: return False
    text = clean_invisible_chars(str(text).lower())
    if re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text): return True
    bad_extensions = ["webhook", "ngrok", "localhost", "0.0.0.0", ".sh", ".txt", "payload", ".exe", ".bat", ".vbs", ".cmd", ".py", ".php"]
    if any(ext in text for ext in bad_extensions): return True
    dangerous_chars = ["rm -rf", "wget ", "curl ", "chmod ", "bash -c", "eval("]
    if any(char in text for char in dangerous_chars): return True
    return False

def bouncer_check(_, __, message: Message):
    if not message.text: return True
    text = clean_invisible_chars(message.text.lower())
    dangerous_symbols = ["ifs", "/etc/passwd", ".env", "webhook.site", "rm -rf", "wget ", "curl ", "chmod ", "bash -c", "eval("]
    if any(sym in text for sym in dangerous_symbols): return False 
    return True

god_mode_filter = filters.create(bouncer_check)

async def send_security_log(message: Message, breach_type: str, payload: str):
    try:
        chat_id = message.chat.id
        chat_title = message.chat.title
        user_mention = message.from_user.mention
        user_id = message.from_user.id
        log_text = f"**🚨 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: {breach_type} 🚨**\n\n**👤 ᴜsᴇʀ:** {user_mention} (`{user_id}`)\n**🏠 ᴄʜᴀᴛ:** {chat_title} (`{chat_id}`)\n**⚠️ ᴘᴀʏʟᴏᴀᴅ:** `{payload}`"
        await app.send_message(config.LOGGER_ID, text=log_text)
    except Exception: pass

def get_random_img(img_list):
    if img_list:
        if isinstance(img_list, list): return random.choice(img_list)
        return img_list
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

def clean_youtube_url(url):
    if not isinstance(url, str): return url, None, "unknown"
    list_match = re.search(r"list=([a-zA-Z0-9_-]+)", url)
    if list_match and ("youtube.com" in url or "youtu.be" in url): return f"https://www.youtube.com/playlist?list={list_match.group(1)}", list_match.group(1), "playlist"
    yt_match = re.search(r"(?:v=|youtu\.be/|shorts/|live/|embed/|watch\?v=|music\.youtube\.com/watch\?v=|/v/)([a-zA-Z0-9_-]{11})", url)
    if yt_match: return f"https://www.youtube.com/watch?v={yt_match.group(1)}", yt_match.group(1), "video"
    return url, None, "unknown"

@app.on_message(filters.command(["play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"]) & filters.group & ~BANNED_USERS & god_mode_filter)
@PlayWrapper
async def play_commnd(client, message: Message, _, chat_id, video, channel, playmode, url, fplay):
    mystic = await message.reply_text(_["play_2"].format(channel) if channel else _["play_1"])
    plist_id, slider, plist_type, spotify = None, None, None, None
    user_id, user_name = message.from_user.id, message.from_user.first_name
    audio_telegram = ((message.reply_to_message.audio or message.reply_to_message.voice) if message.reply_to_message else None)
    video_telegram = ((message.reply_to_message.video or message.reply_to_message.document) if message.reply_to_message else None)
    if audio_telegram:
        if audio_telegram.file_size > 104857600: return await mystic.edit_text(_["play_5"])
        if (audio_telegram.duration) > config.DURATION_LIMIT: return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, app.mention))
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {"title": file_name, "link": message_link, "path": file_path, "dur": dur}
            if is_nsfw_content(details.get("title", "")):
                await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
                return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
            try: await stream(_, mystic, user_id, details, chat_id, user_name, message.chat.id, streamtype="telegram", forceplay=fplay)
            except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            return await mystic.delete()
        return
    elif video_telegram:
        if message.reply_to_message.document:
            try:
                if video_telegram.file_name.split(".")[-1].lower() not in formats: return await mystic.edit_text(_["play_7"].format(f"{' | '.join(formats)}"))
            except: return await mystic.edit_text(_["play_7"].format(f"{' | '.join(formats)}"))
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT: return await mystic.edit_text(_["play_8"])
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {"title": file_name, "link": message_link, "path": file_path, "dur": dur}
            if is_nsfw_content(details.get("title", "")):
                await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
                return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
            try: await stream(_, mystic, user_id, details, chat_id, user_name, message.chat.id, video=True, streamtype="telegram", forceplay=fplay)
            except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            return await mystic.delete()
        return
    elif url:
        if not url.startswith(("http://", "https://")): return await mystic.edit_text("❌ **Security Error:** Local files are not allowed.")
        if is_malicious_link(url):
            await send_security_log(message, "ᴍᴀʟɪᴄɪᴏᴜs ʜᴀᴄᴋ ʟɪɴᴋ", url)
            return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴍᴀʟɪᴄɪᴏᴜs ʟɪɴᴋ ʙʟᴏᴄᴋᴇᴅ!**")
        if is_nsfw_content(url):
            await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", url)
            return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
        if await YouTube.exists(url):
            clean_url, ext_id, y_type = clean_youtube_url(url)
            if y_type == "playlist" or "playlist" in url:
                try: details = await YouTube.playlist(clean_url if y_type == "playlist" else url, config.PLAYLIST_FETCH_LIMIT, message.from_user.id)
                except: return await mystic.edit_text(_["play_3"])
                streamtype, plist_type, img, cap = "playlist", "yt", get_random_img(config.PLAYLIST_IMG_URL), _["play_9"]
                if y_type == "playlist": plist_id = ext_id
                else: plist_id = (url.split("=")[1]).split("&")[0] if "&" in url else url.split("=")[1]
            else:
                try: details, track_id = await YouTube.track(clean_url if y_type == "video" else url)
                except: return await mystic.edit_text(_["play_3"])
                if is_nsfw_content(details.get("title", "")):
                    await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
                    return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
                streamtype, img, cap = "youtube", details["thumb"], _["play_10"].format(details["title"], details["duration_min"])
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET: return await mystic.edit_text("» sᴘᴏᴛɪғʏ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ʏᴇᴛ.")
            if "track" in url:
                try: details, track_id = await Spotify.track(url)
                except: return await mystic.edit_text(_["play_3"])
                if is_nsfw_content(details.get("title", "")):
                    await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
                    return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
                streamtype, img, cap = "youtube", details["thumb"], _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try: details, plist_id = await Spotify.playlist(url)
                except: return await mystic.edit_text(_["play_3"])
                streamtype, plist_type, img, cap = "playlist", "spplay", get_random_img(config.SPOTIFY_PLAYLIST_IMG_URL), _["play_11"].format(app.mention, message.from_user.mention)
            elif "album" in url:
                try: details, plist_id = await Spotify.album(url)
                except: return await mystic.edit_text(_["play_3"])
                streamtype, plist_type, img, cap = "playlist", "spalbum", get_random_img(config.SPOTIFY_ALBUM_IMG_URL), _["play_11"].format(app.mention, message.from_user.mention)
            elif "artist" in url:
                try: details, plist_id = await Spotify.artist(url)
                except: return await mystic.edit_text(_["play_3"])
                streamtype, plist_type, img, cap = "playlist", "spartist", get_random_img(config.SPOTIFY_ARTIST_IMG_URL), _["play_11"].format(message.from_user.first_name)
            else: return await mystic.edit_text(_["play_15"])
        elif await Apple.valid(url):
            if "album" in url:
                try: details, track_id = await Apple.track(url)
                except: return await mystic.edit_text(_["play_3"])
                if is_nsfw_content(details.get("title", "")):
                    await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
                    return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
                streamtype, img, cap = "youtube", details["thumb"], _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try: details, plist_id = await Apple.playlist(url)
                except: return await mystic.edit_text(_["play_3"])
                streamtype, plist_type, cap, img = "playlist", "apple", _["play_12"].format(app.mention, message.from_user.mention), url
            else: return await mystic.edit_text(_["play_3"])
        elif await Resso.valid(url):
            try: details, track_id = await Resso.track(url)
            except: return await mystic.edit_text(_["play_3"])
            if is_nsfw_content(details.get("title", "")):
                await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
                return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
            streamtype, img, cap = "youtube", details["thumb"], _["play_10"].format(details["title"], details["duration_min"])
        elif await SoundCloud.valid(url):
            try: details, track_path = await SoundCloud.download(url)
            except: return await mystic.edit_text(_["play_3"])
            if details["duration_sec"] > config.DURATION_LIMIT: return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, app.mention))
            try: await stream(_, mystic, user_id, details, chat_id, user_name, message.chat.id, streamtype="soundcloud", forceplay=fplay)
            except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            return await mystic.delete()
        else:
            try: await Lucky.stream_call(url)
            except NoActiveGroupCall:
                await mystic.edit_text(_["black_9"])
                return await app.send_message(chat_id=config.LOGGER_ID, text=_["play_17"])
            except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            await mystic.edit_text(_["str_2"])
            try: await stream(_, mystic, message.from_user.id, url, chat_id, message.from_user.first_name, message.chat.id, video=video, streamtype="index", forceplay=fplay)
            except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            return await play_logs(message, streamtype="M3u8 or Index Link")
    else:
        if len(message.command) < 2: return await mystic.edit_text(_["play_18"], reply_markup=InlineKeyboardMarkup(botplaylist_markup(_)))
        slider, query = True, message.text.split(None, 1)[1]
        if "-v" in query: query = query.replace("-v", "")
        clean_url, ext_id, y_type = clean_youtube_url(query)
        if y_type == "video": query = clean_url
        if is_nsfw_content(query):
            await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", query)
            return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
        try: details, track_id = await YouTube.track(query)
        except: return await mystic.edit_text(_["play_3"])
        if is_nsfw_content(details.get("title", "")):
            await send_security_log(message, "ɴsғᴡ ᴠɪᴏʟᴀᴛɪᴏɴ", details.get("title", ""))
            return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
        streamtype = "youtube"
    if str(playmode) == "Direct":
        if not plist_type:
            if details["duration_min"]:
                if time_to_seconds(details["duration_min"]) > config.DURATION_LIMIT: return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, app.mention))
            else: return await mystic.edit_text(_["play_13"], reply_markup=InlineKeyboardMarkup(livestream_markup(_, track_id, user_id, "v" if video else "a", "c" if channel else "g", "f" if fplay else "d")))
        try: await stream(_, mystic, user_id, details, chat_id, user_name, message.chat.id, video=video, streamtype=streamtype, spotify=spotify, forceplay=fplay)
        except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
        await mystic.delete()
        return await play_logs(message, streamtype=streamtype)
    else:
        if plist_type:
            ran_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            lyrical[ran_hash] = plist_id
            await mystic.delete()
            return await message.reply_photo(photo=img, caption=cap, reply_markup=InlineKeyboardMarkup(playlist_markup(_, ran_hash, message.from_user.id, plist_type, "c" if channel else "g", "f" if fplay else "d")), has_spoiler=True)
        else:
            await mystic.delete()
            if slider: return await message.reply_photo(photo=details["thumb"], caption=_["play_10"].format(details["title"].title(), details["duration_min"]), reply_markup=InlineKeyboardMarkup(slider_markup(_, track_id, message.from_user.id, query, 0, "c" if channel else "g", "f" if fplay else "d")), has_spoiler=True)
            else: return await message.reply_photo(photo=img, caption=cap, reply_markup=InlineKeyboardMarkup(track_markup(_, track_id, message.from_user.id, "c" if channel else "g", "f" if fplay else "d")), has_spoiler=True)

@app.on_callback_query(filters.regex("MusicStream") & ~BANNED_USERS)
@languageCB
async def play_music(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    vidid, user_id, mode, cplay, fplay = callback_data.split(None, 1)[1].split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try: return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except: return
    try: chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except: return
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except: pass
    mystic = await CallbackQuery.message.reply_text(_["play_2"].format(channel) if channel else _["play_1"])
    try: details, track_id = await YouTube.track(vidid, True)
    except: return await mystic.edit_text(_["play_3"])
    if is_nsfw_content(details.get("title", "")): return await mystic.edit_text("**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
    if details["duration_min"]:
        if time_to_seconds(details["duration_min"]) > config.DURATION_LIMIT: return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, app.mention))
    else: return await mystic.edit_text(_["play_13"], reply_markup=InlineKeyboardMarkup(livestream_markup(_, track_id, CallbackQuery.from_user.id, mode, "c" if cplay == "c" else "g", "f" if fplay else "d")))
    try: await stream(_, mystic, CallbackQuery.from_user.id, details, chat_id, CallbackQuery.from_user.first_name, CallbackQuery.message.chat.id, True if mode == "v" else None, streamtype="youtube", forceplay=True if fplay == "f" else None)
    except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
    return await mystic.delete()

@app.on_callback_query(filters.regex("LuckymousAdmin") & ~BANNED_USERS)
async def Luckymous_check(client, CallbackQuery):
    try: await CallbackQuery.answer("» ʀᴇᴠᴇʀᴛ ʙᴀᴄᴋ ᴛᴏ ᴜsᴇʀ ᴀᴄᴄᴏᴜɴᴛ :\n\nᴏᴘᴇɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ sᴇᴛᴛɪɴɢs.\n-> ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs\n-> ᴄʟɪᴄᴋ ᴏɴ ʏᴏᴜʀ ɴᴀᴍᴇ\n-> ᴜɴᴄʜᴇᴄᴋ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs.", show_alert=True)
    except: pass

@app.on_callback_query(filters.regex("LuckyPlaylists") & ~BANNED_USERS)
@languageCB
async def play_playlists_command(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    videoid, user_id, ptype, mode, cplay, fplay = callback_data.split(None, 1)[1].split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try: return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except: return
    try: chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except: return
    await CallbackQuery.message.delete()
    try: await CallbackQuery.answer()
    except: pass
    mystic = await CallbackQuery.message.reply_text(_["play_2"].format(channel) if channel else _["play_1"])
    videoid = lyrical.get(videoid)
    if ptype == "yt":
        try: result = await YouTube.playlist(videoid, config.PLAYLIST_FETCH_LIMIT, CallbackQuery.from_user.id, True)
        except: return await mystic.edit_text(_["play_3"])
    elif ptype == "spplay":
        try: result, spotify_id = await Spotify.playlist(videoid)
        except: return await mystic.edit_text(_["play_3"])
    elif ptype == "spalbum":
        try: result, spotify_id = await Spotify.album(videoid)
        except: return await mystic.edit_text(_["play_3"])
    elif ptype == "spartist":
        try: result, spotify_id = await Spotify.artist(videoid)
        except: return await mystic.edit_text(_["play_3"])
    elif ptype == "apple":
        try: result, apple_id = await Apple.playlist(videoid, True)
        except: return await mystic.edit_text(_["play_3"])
    try: await stream(_, mystic, user_id, result, chat_id, CallbackQuery.from_user.first_name, CallbackQuery.message.chat.id, True if mode == "v" else None, streamtype="playlist", spotify=True if ptype != "yt" else False, forceplay=True if fplay == "f" else None)
    except Exception as e: return await mystic.edit_text(_["general_2"].format(type(e).__name__))
    return await mystic.delete()

@app.on_callback_query(filters.regex("slider") & ~BANNED_USERS)
@languageCB
async def slider_queries(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    what, rtype, query, user_id, cplay, fplay = callback_data.split(None, 1)[1].split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try: return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except: return
    try: await CallbackQuery.answer(_["playcb_2"])
    except: pass
    query_type = int(rtype)
    if str(what) == "F": query_type = 0 if query_type == 9 else query_type + 1
    else: query_type = 9 if query_type == 0 else query_type - 1
    title, duration_min, thumbnail, vidid = await YouTube.slider(query, query_type)
    if is_nsfw_content(title):
        try: await CallbackQuery.message.delete()
        except: pass
        return await app.send_message(CallbackQuery.message.chat.id, "**🚫 sᴇᴄᴜʀɪᴛʏ ᴀʟᴇʀᴛ: ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏʜɪʙɪᴛᴇᴅ!**")
    return await CallbackQuery.edit_message_media(media=InputMediaPhoto(media=thumbnail, caption=_["play_10"].format(title.title(), duration_min), has_spoiler=True), reply_markup=InlineKeyboardMarkup(slider_markup(_, vidid, user_id, query, query_type, cplay, fplay)))
