RespawnNationBackend

Live beta - https://respawnnation.site/
Project explanation - https://me-bw1.pages.dev/respawn-nation

Backend API for Respawn Nation, an esports platform for hosting competitive tournaments, live streaming gameplay, and managing prize distributions.
Tech Stack

    Framework: Django / Django REST Framework

    Database: PostgreSQL

    Caching: Redis (django-redis)

    Live Streaming: Cloudflare Stream API

    Payments: Razorpay

Features

    Tournament Bracket Engine: Custom logic for generating tournament brackets, handling match progression, and updating standings.

    Streaming API: Cloudflare Stream integration for low-latency live video feeds and playback.

    Cached Feeds: Redis caching on heavy read endpoints (/api/games/browse_games/, trending feeds) to reduce database queries.

    Payments: Razorpay integration for ticket purchases and wallet transactions.

    Real-time Chat: WebSocket and REST routes for tournament/global/game chat rooms.

Getting Started
Prerequisites

    Python 3.11+

    PostgreSQL

    Redis server running locally (localhost:6379)

Setup

    Clone repo & set up environment
    Bash

    git clone https://github.com/your-username/RespawnNationBackend.git
    cd RespawnNationBackend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    Configure Environment Variables
    Create a .env file in the root folder:
    Code snippet

    DEBUG=True
    SECRET_KEY=your_secret_key
    DATABASE_URL=postgres://user:password@localhost:5432/respawn_db
    REDIS_URL=redis://127.0.0.1:6379/1

    RAZORPAY_KEY_ID=your_razorpay_key
    RAZORPAY_KEY_SECRET=your_razorpay_secret

    CLOUDFLARE_ACCOUNT_ID=your_cloudflare_id
    CLOUDFLARE_STREAM_API_TOKEN=your_cloudflare_token

    Database Migration & Run
    Bash

    python manage.py migrate
    python manage.py runserver

