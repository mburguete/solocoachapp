# SoloCoach — your personal daily planner (Palma/Madrid + flights + training + habits)

A lightweight Flask app that generates a **scripted day** for you, sends **Telegram check-ins**,
and turns **airport time into focused work sprints**. Fully local, free, and easy to deploy.

## Features
- Plan generator that uses your **Palma/Madrid rhythm**, **flights**, and **weather** to schedule:
  - Morning training (endurance in Palma, gym/brick in Madrid)
  - Protein + creatine reminders
  - Airport deep-work sprints from your task list
- **Telegram** morning plan + evening check-in (free)
- **Streaks** for Training, Protein+Creatine, and Deep-Work
- Google Calendar **optional** export (`.ics` download) for the day's plan
- Timezone-aware (defaults to `Africa/Ceuta`)

## Quickstart (local)
1. Install deps (Python 3.10+ recommended)
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file:
   ```
   FLASK_SECRET=change-me
   TZ=Africa/Ceuta
   TELEGRAM_BOT_TOKEN=123456:ABC...      # optional but recommended
   TELEGRAM_CHAT_ID=123456789            # your chat id
   HOME_CITY_PALMA=Palma de Mallorca
   HOME_CITY_MADRID=Madrid
   ```
3. Run
   ```bash
   flask --app app run --debug
   ```
4. Open http://127.0.0.1:5000

## Deploy free
- **Render.com**: Web Service (free) + Cron Job (call `/cron/morning` 07:00 and `/cron/evening` 21:00 CE(S)T)
- **Fly.io / Railway**: similar setup; set env vars.

## What it doesn't do (yet)
- OAuth or multi-user (it's just for you)
- Bi-directional Google Calendar sync (exports `.ics` for import)
