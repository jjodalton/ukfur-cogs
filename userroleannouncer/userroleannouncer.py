import logging
from datetime import datetime, timezone
from pprint import pformat
from typing import Union

import discord
from redbot.core import commands
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n, set_contextual_locales_from_guild
from redbot.core.utils import AsyncIter
from redbot.core.utils import chat_formatting as chat
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


def is_channel_set(channel_type: str):
    """Checks if server has set channel for logging"""

    async def predicate(ctx):
        if ctx.guild:
            return ctx.guild.get_channel(
                await getattr(ctx.cog.config.guild(ctx.guild), f"{channel_type}_channel")()
            )

    return commands.check(predicate)


async def ignore_config_add(config: list, item):
    """Adds item to provided config list"""
    if item.id in config:
        config.remove(item.id)
    else:
        config.append(item.id)


log = logging.getLogger("red.ukfur-cogs.userroleannouncer")
_ = Translator("MessagesLog", __file__)


@cog_i18n(_)
class UserRoleAnnouncer(commands.Cog):
    """Joins and boosts announced to specific channel"""

    __version__ = "1"

    # noinspection PyMissingConstructor

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0x908013f521d18c81c3356ce8)
        default_guild = {
            "join_channel": None,
            "boost_channel": None,
            "joining": True,
            "boosting": True,
            "ignored_users": [],
        }
        self.config.register_guild(**default_guild)

    async def initialize(self):
        """
        Update configs if required

        Versions:
        """
        pass

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\n**Version**: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.group(autohelp=True, aliases=["userrolesannouncer", "rolesannouncer", "roleannouncer"])
    @commands.admin_or_permissions(manage_guild=True)
    async def userroleannouncer(self, ctx):
        """Manage member role announcements"""
        pass

    @userroleannouncer.group(name="channel")
    async def set_channel(self, ctx):
        """Set the channels for announcements"""
        pass

    @set_channel.command(name="join")
    async def join_channel(self, ctx, *, channel: discord.TextChannel = None):
        """Set the channel for join logs

        If channel is not specified, then announcements will be disabled"""
        await self.config.guild(ctx.guild).join_channel.set(channel.id if channel else None)
        await ctx.tick()

    @set_channel.command(name="boost")
    async def boost_channel(self, ctx, *, channel: discord.TextChannel = None):
        """Set the channel for boost logs

        If channel is not specified, then announcements will be disabled"""
        await self.config.guild(ctx.guild).boost_channel.set(channel.id if channel else None)
        await ctx.tick()

    @set_channel.command(name="all")
    async def all_channel(self, ctx, *, channel: discord.TextChannel = None):
        """Set the channel for all logs

        If channel is not specified, then announcements will be disabled"""
        await self.config.guild(ctx.guild).join_channel.set(channel.id if channel else None)
        await self.config.guild(ctx.guild).boost_channel.set(channel.id if channel else None)
        await ctx.tick()

    @set_channel.command(name="settings")
    async def channel_settings(self, ctx):
        """View current channels settings"""
        settings = []
        if join := await self.config.guild(ctx.guild).join_channel():
            settings.append(_("Join: {}").format(ctx.guild.get_channel(join)))
        if boost := await self.config.guild(ctx.guild).boost_channel():
            settings.append(_("Boost: {}").format(ctx.guild.get_channel(boost)))
        await ctx.send("\n".join(settings) or chat.info(_("No channels set")))

    @userroleannouncer.group()
    async def toggle(self, ctx):
        """Toggle announcements"""
        pass

    @toggle.command(name="join")
    @is_channel_set("join")
    async def mess_join(self, ctx):
        """Toggle logging of join message"""
        joining = self.config.guild(ctx.guild).joining
        await joining.set(not await joining())
        state = _("enabled") if await self.config.guild(ctx.guild).joining() else _("disabled")
        await ctx.send(chat.info(_("Join announcement {}").format(state)))

    @toggle.command(name="boost")
    @is_channel_set("boost")
    async def mess_leave(self, ctx):
        """Toggle logging of boost message"""
        boosting = self.config.guild(ctx.guild).boosting
        await boosting.set(not await boosting())
        state = _("enabled") if await self.config.guild(ctx.guild).boosting() else _("disabled")
        await ctx.send(chat.info(_("Boost announcement {}").format(state)))

    @userroleannouncer.command()
    async def ignore(
            self,
            ctx,
            *ignore: Union[discord.Member, discord.TextChannel, discord.CategoryChannel],
    ):
        """
        Manage message logging blocklist
        Shows blocklist if no arguments provided
        You can ignore members
        If item is in blocklist, removes it
        """
        if not ignore:
            users = await self.config.guild(ctx.guild).ignored_users()
            users = [ctx.guild.get_member(m).mention for m in users if ctx.guild.get_member(m)]
            if not users:
                await ctx.send(chat.info(_("Nothing is ignored")))
                return
            users_pages = [
                discord.Embed(title=_("Ignored users"), description=page)
                for page in chat.pagify("\n".join(users), page_length=2048)
            ]

            pages = users_pages
            await menu(ctx, pages, DEFAULT_CONTROLS)
        else:
            guild = self.config.guild(ctx.guild)
            for item in ignore:
                if isinstance(item, discord.Member):
                    async with guild.ignored_users() as ignored_users:
                        await ignore_config_add(ignored_users, item)
            await ctx.tick()

    """
    This is our listener for members boosting.
    """
    @commands.Cog.listener("on_member_update")
    async def message_user_boost(self, before: discord.Member, after: discord.Member):
        # If there is no message then return
        if not before.guild or not after.guild:
            log.debug("user_boost: not member.guild return")
            return

        #  if the bot is disabled in the message server then return
        if await self.bot.cog_disabled_in_guild(self, before.guild):
            log.debug("user_boost: cog disabled in guild return")
            return

        # try to get the logging channel for the messages server
        logchannel = before.guild.get_channel(
            await self.config.guild(before.guild).boost_channel()
        )

        # if the logging channel isn't set then return
        if not logchannel:
            log.debug("user_boost: No logchannel return")
            return

        # translate the message to be logged based on server locale
        await set_contextual_locales_from_guild(self.bot, before.guild)

        # check the users before and after roles are different
        if before.roles == after.roles:
            log.debug("user_boost: roles are equal return")
            return

        # check if the supporter role is in before.roles
        if 'Supporter' in before.roles:
            log.debug("user_boost: User already boosting return")
            return

        # start building the log message
        embed = discord.Embed(
            title=_("User Boosted"),
            description=chat.inline(_("User has boosted the server")),
            timestamp=datetime.now(timezone.utc),
            colour=discord.Colour.purple(),
        )

        # get message author from incoming message
        embed.set_author(name=before.name, icon_url=before.avatar_url)

        # try to send the message
        try:
            await logchannel.send(embed=embed)
        # if we don't have permission then ignore it
        except discord.Forbidden:
            pass
