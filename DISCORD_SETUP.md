## Discord bot token

`bot.py` reads the bot token from the `DISCORD_TOKEN` environment variable:

```text
DISCORD_TOKEN=YOUR_NEW_BOT_TOKEN
```

For Render, add `DISCORD_TOKEN` under the service's Environment Variables/Secrets.
Do not commit a real token to the source repository.

The token previously pasted into chat should not be reused; generate a fresh token in the Discord Developer Portal.
