import random
from repthon import zq_lo
from repthon.utils import admin_cmd
from random import choice
from telethon import events

baqir = [
  "**مطوري باقر فديته**",
  "**احبككككككك مطوري**"
]


@zq_lo.on(events.NewMessage(pattern="منو مطورك"))
async def baqir_dev(baqir):
  user = await event.get_sender()
  rep_dev = (5502537272)
    await baqir.edit(choice(baqir))
