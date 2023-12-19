import asyncio
import contextlib
import os
import sys
from asyncio.exceptions import CancelledError
from time import sleep

import heroku3
import urllib3
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from . import HEROKU_APP, UPSTREAM_REPO_URL, zq_lo

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.utils import _reputils
from ..sql_helper.global_collection import (
    add_to_collectionlist,
    del_keyword_collectionlist,
    get_collectionlist_items,
)

plugin_category = "الادوات"
cmdhd = Config.COMMAND_HAND_LER
ENV = bool(os.environ.get("ENV", False))
LOGS = logging.getLogger(__name__)
# -- Constants -- #

HEROKU_APP_NAME = Config.HEROKU_APP_NAME or None
HEROKU_API_KEY = Config.HEROKU_API_KEY or None
Heroku = heroku3.from_key(Config.HEROKU_API_KEY)
OLDZED = Config.OLDZED
heroku_api = "https://api.heroku.com"

UPSTREAM_REPO_BRANCH = "main"

REPO_REMOTE_NAME = "temponame"
IFFUCI_ACTIVE_BRANCH_NAME = "main"
NO_HEROKU_APP_CFGD = "no heroku application found, but a key given? 😕 "
HEROKU_GIT_REF_SPEC = "HEAD:refs/heads/lite"
RESTARTING_APP = "re-starting heroku application"
IS_SELECTED_DIFFERENT_BRANCH = (
    "looks like a custom branch {branch_name} "
    "is being used:\n"
    "in this case, Updater is unable to identify the branch to be updated."
    "please check out to an official branch, and re-start the updater."
)


# -- Constants End -- #

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

requirements_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "requirements.txt"
)


async def gen_chlog(repo, diff):
    d_form = "%d/%m/%y"
    return "".join(
        f"  • {c.summary} ({c.committed_datetime.strftime(d_form)}) <{c.author}>\n"
        for c in repo.iter_commits(diff)
    )


async def update_requirements():
    reqs = str(requirements_path)
    try:
        process = await asyncio.create_subprocess_shell(
            " ".join([sys.executable, "-m", "pip", "install", "-r", reqs]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        return process.returncode
    except Exception as e:
        return repr(e)


async def update_bot(event, repo, ups_rem, ac_br):
    try:
        ups_rem.pull(ac_br)
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")
    await update_requirements()
    sandy = await event.edit(f"JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**•⎆┊تم التحـديث ⎌ بنجـاح**\n**•⎆┊جـارِ إعـادة تشغيـل بـوت ريبـــثون ⎋ **\n**•⎆┊انتظـࢪ مـن 2 - 1 دقيقـه . . .📟**")
    await event.client.reload(sandy)


async def deploy(event, repo, ups_rem, ac_br, txt):
    if HEROKU_API_KEY is None:
        return await event.edit(f"JERUSALEM - تحـديثـات السـورس\n **•─────────────────•**\n** ⪼ لم تقـم بوضـع مربـع فـار HEROKU_API_KEY اثنـاء التنصيب وهـذا خطـأ .. قم بضبـط المتغيـر أولاً لتحديث بوت ريبـــثون ..؟!**", link_preview=False)
    heroku = heroku3.from_key(HEROKU_API_KEY)
    heroku_applications = heroku.apps()
    if HEROKU_APP_NAME is None:
        await event.edit(f"JERUSALEM - تحـديثـات السـورس\n **•─────────────────•**\n** ⪼ لم تقـم بوضـع مربـع فـار HEROKU_APP_NAME اثنـاء التنصيب وهـذا خطـأ .. قم بضبـط المتغيـر أولاً لتحديث بوت ريبـــثون ..؟!**", link_preview=False)
        repo.__del__()
        return
    heroku_app = next(
        (app for app in heroku_applications if app.name == HEROKU_APP_NAME),
        None,
    )

    if heroku_app is None:
        await event.edit(
            f"{txt}\n" "**- بيانات اعتماد هيروكو غير صالحة لتنصيب تحديث ريبـــثون**"
        )
        return repo.__del__()
    sandy = await event.edit(f"JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**✾╎جـارِ . . تنصـيب التحـديث الجـذري ⎌**\n**✾╎يـرجى الانتظـار حتى تنتـهي العمليـة ⎋**\n**✾╎عادة ما يستغرق هـذا التحديث من 5 - 4 دقائـق 📟**")
    try:
        ulist = get_collectionlist_items()
        for i in ulist:
            if i == "restart_update":
                del_keyword_collectionlist("restart_update")
    except Exception as e:
        LOGS.error(e)
    try:
        add_to_collectionlist("restart_update", [sandy.chat_id, sandy.id])
    except Exception as e:
        LOGS.error(e)
    ups_rem.fetch(ac_br)
    repo.git.reset("--hard", "FETCH_HEAD")
    heroku_git_url = heroku_app.git_url.replace(
        "https://", f"https://api:{HEROKU_API_KEY}@"
    )

    if "heroku" in repo.remotes:
        remote = repo.remote("heroku")
        remote.set_url(heroku_git_url)
    else:
        remote = repo.create_remote("heroku", heroku_git_url)
    try:
        remote.push(refspec="HEAD:refs/heads/lite", force=True)
    except Exception as error:
        await event.edit(f"{txt}\n**Error log:**\n`{error}`")
        return repo.__del__()
    build_status = heroku_app.builds(order_by="created_at", sort="desc")[0]
    if build_status.status == "failed":
        return await edit_delete(
            event, "`Build failed!\n" "Cancelled or there were some errors...`"
        )
    try:
        remote.push("main", force=True)
    except Exception as error:
        await event.edit(f"{txt}\n**Here is the error log:**\n`{error}`")
        return repo.__del__()
    await event.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**•⎆┊انت منصب التحديث سابقـاً 🤷🏻‍♀\n•⎆┊لـذلك سـوف يتـم إعـادة التشغيـل فقـط 🌐 **")
    with contextlib.suppress(CancelledError):
        await event.client.disconnect()
        if HEROKU_APP is not None:
            HEROKU_APP.restart()

@zq_lo.rep_cmd(
    pattern="تحديث البوت$",
)
async def upstream(event):
    if ENV:
        if HEROKU_API_KEY is None or HEROKU_APP_NAME is None:
            return await edit_or_reply(
                event, "**- بيانات اعتماد تنصيبك غير صالحة لتنصيب تحديث ريبـــثون ❕❌**\n**- يجب تعييـن قيـم مربعـات الفارات التالية يدوياً من حساب هيروكـو 🛂**\n\n\n**- مربـع مفتـاح هيروكـو :** HEROKU_API_KEY\n**- مربـع اسـم التطبيـق :** HEROKU_APP_NAME"
            )
    elif os.path.exists("config.py"):
        return await edit_delete(
            event,
            f"I guess you are on selfhost. For self host you need to use `{cmdhd}تحديث الان`",
        )
    event = await edit_or_reply(event, f"JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⪼ يتم تنصيب التحديث انتظر 🌐 ،**")
    off_repo = "https://github.com/RepthonArabic/Palestine"
    os.chdir("/app")
    try:
        txt = (
            "`Oops.. Updater cannot continue due to "
            + "some problems occured`\n\n**LOGTRACE:**\n"
        )

        repo = Repo()
    except NoSuchPathError as error:
        await event.edit(f"{txt}\n`directory {error} is not found`")
        return repo.__del__()
    except GitCommandError as error:
        await event.edit(f"{txt}\n`Early failure! {error}`")
        return repo.__del__()
    except InvalidGitRepositoryError:
        repo = Repo.init()
        origin = repo.create_remote("upstream", off_repo)
        origin.fetch()
        repo.create_head("lite", origin.refs.lite)
        repo.heads.lite.set_tracking_branch(origin.refs.lite)
        repo.heads.lite.checkout(True)
    with contextlib.suppress(BaseException):
        repo.create_remote("upstream", off_repo)
    bbb1 = await event.edit(f"JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**")
    await asyncio.sleep(1)
    bbb2 = await bbb1.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟷𝟶 ▬▭▭▭▭▭▭▭▭▭")
    await asyncio.sleep(1)
    bbb3 = await bbb2.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟸𝟶 ▬▬▭▭▭▭▭▭▭▭")
    await asyncio.sleep(1)
    bbb4 = await bbb3.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟹𝟶 ▬▬▬▭▭▭▭▭▭▭")
    await asyncio.sleep(1)
    bbb5 = await bbb4.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟺𝟶 ▬▬▬▬▭▭▭▭▭▭")
    await asyncio.sleep(1)
    bbb6 = await bbb5.edit("JERUSALEMJERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟻𝟶 ▬▬▬▬▬▭▭▭▭▭")
    await asyncio.sleep(1)
    bbb7 = await bbb6.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟼𝟶 ▬▬▬▬▬▬▭▭▭▭")
    await asyncio.sleep(1)
    bbb8 = await bbb7.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟽𝟶 ▬▬▬▬▬▬▬▭▭▭")
    await asyncio.sleep(1)
    bbb9 = await bbb8.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟾𝟶 ▬▬▬▬▬▬▬▬▭▭") 
    await asyncio.sleep(1)
    bbbb10 = await bbb9.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟿𝟶 ▬▬▬▬▬▬▬▬▬▭") 
    await asyncio.sleep(1)
    bbbb11 = await bbbb10.edit("JERUSALEM - تحـديثـات السـورس\n**•─────────────────•**\n\n**⇜ يتـم تحـديث بـوت ريبـــثون .. انتظـر . . .🌐**\n\n%𝟷𝟶𝟶 ▬▬▬▬▬▬▬▬▬▬💯") 
    ac_br = repo.active_branch.name
    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)
    await deploy(bbbb11, repo, ups_rem, ac_br, txt)
