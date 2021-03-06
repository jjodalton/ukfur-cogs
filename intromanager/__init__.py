from .introchannelmanager import IntroChannelManager

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


async def setup(bot):
    cog = IntroChannelManager(bot)
    await cog.initialize()
    bot.add_cog(cog)
