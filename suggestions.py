import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
import datetime

load_dotenv()
SUGGESTION_CHANNEL_ID = int(os.getenv("SUGGESTION_CHANNEL_ID"))

class SuggestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggestion",
        description="Send a suggestion for the server (DM only)"
    )
    async def suggestion(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str
    ):
        # If used in a server, tell user to check DMs and send instructions
        if interaction.guild is not None:
            await interaction.response.send_message(
                "Check your DMs! You can only use /suggestion in DMs. Instructions have been sent.", ephemeral=True
            )
            try:
                await interaction.user.send(
                    "Hi! To submit a suggestion, please DM me and use the /suggestion command followed by your suggestion."
                )
            except Exception:
                pass
            return

        suggestion_channel = self.bot.get_channel(SUGGESTION_CHANNEL_ID)
        if suggestion_channel is None:
            await interaction.response.send_message("Suggestion channel not found. Please contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description=user_input,
            color=discord.Color(0xb8effc),
        )
        embed.set_author(
            name=f"{interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(name="User", value=f"<@{interaction.user.id}>", inline=True)
        embed.add_field(name="Time", value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>", inline=True)

        await suggestion_channel.send(embed=embed)
        await interaction.response.send_message(
            "Your suggestion has been sent! Thank you for helping improve the server <a:aliceclap:1396972200291995680>", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only respond to DMs that are not from bots and not using the slash command
        if message.guild is None and not message.author.bot:
            # Ignore if message is a slash command (they don't show up as normal messages)
            if not message.content.startswith("/"):
                await message.channel.send(
                    "Hi! You can only submit suggestions using the suggestion command. Please type `/suggestion [your suggestion here]`."
                )

async def setup(bot):
    await bot.add_cog(SuggestionCog(bot))