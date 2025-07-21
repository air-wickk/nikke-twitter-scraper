import discord
from discord.ext import commands

class OwnerSync(commands.Cog, name="OwnerSync"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Only allow sync from bot owner and only in guilds
        if message.author.bot:
            return
        if (
            self.bot.user.mentioned_in(message)
            and "sync" in message.content.lower()
        ):
            # Optional: restrict to owner only
            app_info = await self.bot.application_info()
            if message.author.id != app_info.owner.id:
                await message.channel.send("Only the bot owner can sync commands.")
                return
            synced = await self.bot.tree.sync()
            await message.channel.send(f"Successfully synced {len(synced)} command(s).")

async def setup(bot):
    await bot.add_cog(OwnerSync(bot))