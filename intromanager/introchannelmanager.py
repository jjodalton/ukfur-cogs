from redbot.core import commands

class IntroChannelManager(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def introchannelmanager(self, ctx):
        """This does stuff!"""
        # Your code will go here
        await ctx.send("I can do stuff!")