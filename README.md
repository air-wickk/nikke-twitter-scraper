# NIKKE Twitter Scraper

This project is a Discord bot that tracks a specified Twitter account (NIKKE_en) and sends its posts to a designated Discord channel. The bot utilizes the Discord.py library for interacting with the Discord API and the Twitter API for fetching tweets.

## Features

- Monitors a specified Twitter account for new tweets and posts them to a Discord channel.
- Slash command `/suggestion` for users to submit feedback, visible only to the user.
- Slash command `/joincode` with a dropdown menu for users to get join codes for various games/guilds, visible only to the user.
- Owner-only sync command (`@Bot sync`) to instantly sync slash commands to the server.
- Self-destructing DM error messages for invalid suggestion attempts.
- Dynamic bot status updates.
- Flask web server for deployment compatibility.
- Configurable via environment variables.