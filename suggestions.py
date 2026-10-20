import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
import datetime

load_dotenv()
SUGGESTION_CHANNEL_ID = int(os.getenv("SUGGESTION_CHANNEL_ID"))

def _card_view(container):
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(container)
    return view

class SuggestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggestion",
        description="Send a suggestion for the server (only visible to you)"
    )
    async def suggestion(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str
    ):
        suggestion_channel = self.bot.get_channel(SUGGESTION_CHANNEL_ID)
        if suggestion_channel is None:
            await interaction.response.send_message(
                "Suggestion channel not found. Please let an admin know!",
                ephemeral=True
            )
            return

        # CV2 card so suggestion posts match the rest of the bot's output
        container = discord.ui.Container(accent_color=discord.Color(0xb8effc))
        header = discord.ui.Section(
            discord.ui.TextDisplay(f"## {title[:250]}\n-# {interaction.user}"),
            accessory=discord.ui.Thumbnail(media=interaction.user.display_avatar.url),
        )
        container.add_item(header)
        container.add_item(discord.ui.TextDisplay(description[:4000]))
        container.add_item(discord.ui.Separator())
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        container.add_item(
            discord.ui.TextDisplay(f"<@{interaction.user.id}> • <t:{now}:F>")
        )
        await suggestion_channel.send(view=_card_view(container))
        await interaction.response.send_message(
            "Your feedback has been sent! Thank you for helping improve the server <a:aliceclap:1396972200291995680>",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only respond to DMs that are not from bots and not using the slash command
        if message.guild is None and not message.author.bot:
            # Ignore if message is a slash command (they don't show up as normal messages)
            if not message.content.startswith("/"):
                expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)
                msg = await message.channel.send(
                    f"Hi! You can only submit suggestions using the `/suggestion` command. This message will self-destruct <t:{int(expiry.timestamp())}:R>."
                )
                await discord.utils.sleep_until(expiry)
                await msg.delete()

async def setup(bot):
    await bot.add_cog(SuggestionCog(bot))