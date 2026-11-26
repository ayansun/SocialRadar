# SocialRadar

SocialRadar is a FastAPI project for Web Programming Fundamentals. It helps freelancers find potential clients by matching social media posts against keyword trackers. Add Bluesky and Threads posts manually or load sample posts with `POST /api/demo/seed`. Data is stored in PostgreSQL and survives server restarts.

## Run locally

Requirements: Python 3.11+ and PostgreSQL 14+ (or Docker).

```
# 1. Start PostgreSQL (Docker). Without Docker, create an empty database
#    named "socialradar" in your own PostgreSQL instead.
docker compose up -d

# 2. Install dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

# 3. Configure the database connection and the JWT secret
cp .env.example .env               # edit DATABASE_URL and SECRET_KEY

# 4. Create the tables from the migrations
alembic upgrade head

# 5. Start the server
python -m uvicorn app.main:app
```

The same server hosts the [web app](http://127.0.0.1:8000/) and [Swagger UI](http://127.0.0.1:8000/docs).

`DATABASE_URL` format: `postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE`.

## Database

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | Accounts | email and username unique; password stored only as a bcrypt hash; `role` is `user` or `admin` |
| `trackers` | Keyword searches | name unique (case-insensitive); keywords and platforms not empty; `owner_id` FK to users |
| `posts` | Social media posts | `(platform, external_id)` unique; platform and source restricted to known values |
| `matches` | A tracker found a post (a lead) | FK to trackers and posts (`ON DELETE CASCADE`); `(tracker_id, post_id)` unique; status restricted to `new/saved/contacted/dismissed` |
| `notifications` | One per new match | FK to matches (`ON DELETE CASCADE`) |

Relationships (one-to-many): `User -> Trackers`, `Tracker -> Matches`, `Post -> Matches`, `Match -> Notifications`. Deleting a tracker or a post removes its matches and their notifications.

Schema changes are managed with Alembic (`alembic/versions/`). After changing a model run `alembic revision --autogenerate -m "description"` and then `alembic upgrade head`. To rebuild the schema from scratch: `alembic downgrade base && alembic upgrade head`.

## Authentication and authorization

- `POST /auth/register` (JSON: `email`, `username`, `password` of 8+ characters) creates a user. A duplicate email or username returns 409. The password is hashed with bcrypt before it is stored.
- `POST /auth/login` (form fields `username` and `password`; `username` can be the email or the username) returns a JWT `access_token`. Wrong credentials return 401.
- `GET /auth/me` returns the current user.
- Every `/api/*` endpoint needs the header `Authorization: Bearer <token>`. A missing, invalid or expired token returns 401. In Swagger (`/docs`) press **Authorize** and log in. In the web app use the login form. `/health` and the web page itself are public.
- `app/dependencies.py` has the reusable dependencies: `get_current_user` (checks the token and loads the user) and `require_admin`.

Access rules:

| Resource | Regular user | Admin |
|---|---|---|
| Trackers | sees, edits and deletes only their own (someone else's returns 403) | all trackers |
| Leads (matches) and notifications | only those of their own trackers (403 otherwise) | all |
| Stats | numbers for their own data | numbers for all data |
| Posts | read all, add new ones (shared by everyone) | also delete posts |
| `POST /api/demo/seed` | 403 | allowed |

Matching still checks every user's trackers when a post arrives, so each user gets leads for their own trackers.

Everyone who registers is a regular user. To make an admin, register the account first and then run `python -m app.create_admin user@example.com`.

## Workflows

1. **Manage trackers.** Create, edit, pause, or delete a tracker. Each tracker has a unique name, at least one keyword, and at least one platform. Creating or editing a tracker rechecks stored posts.
2. **Match posts.** The service checks active trackers for the post's platform. It matches phrases without regard to case, skips posts with excluded phrases, and creates one lead and one notification per matching tracker. Reusing an `external_id` on the same platform returns HTTP 409.
3. **Work through leads.** A new lead can be saved or dismissed. A saved lead can be marked as contacted or dismissed, a contacted lead can be dismissed, and a dismissed lead can be restored to new. Notifications can be marked as read or unread. Deleting a tracker or post removes its leads and their notifications.

## Project structure

- [`app/main.py`](app/main.py) configures FastAPI, registers routers, and handles application errors.
- [`app/api/`](app/api/) defines routes, [`app/schemas/`](app/schemas/) defines Pydantic models, and [`app/services/`](app/services/) implements business rules.
- [`app/models/`](app/models) defines the SQLAlchemy tables, [`app/database.py`](app/database.py) creates the engine and the per-request session (`get_db`), and [`app/config.py`](app/config.py) reads `DATABASE_URL` from the environment. [`alembic/`](alembic) holds the migrations.
- [`static/`](static/) contains the HTML, CSS, and JavaScript interface. [`tests/`](tests/) contains API tests.

## Test the API

Open [Swagger UI](http://127.0.0.1:8000/docs) on a fresh server. Expand a route, select **Try it out**, and use **Execute** to send the request.

1. Send this body to `POST /api/trackers`. Expect **201** and save the tracker ID. Try it again with `"keywords": []` to see **422**.

   ```json
   {
     "name": "Website Leads",
     "keywords": ["нужен сайт"],
     "excluded_keywords": ["бесплатно"],
     "platforms": ["bluesky"]
   }
   ```

2. Send this body to `POST /api/posts`. Expect **201**, `matches_created: 1`, and `notifications_created: 1`.

   ```json
   {
     "platform": "bluesky",
     "external_id": "demo-001",
     "author": "demo.author",
     "text": "Мне НУЖЕН САЙТ для магазина",
     "url": "https://example.com/posts/demo-001"
   }
   ```

3. Call `GET /api/matches` with the `tracker_id` query parameter and copy the new lead's ID. Use it in `PATCH /api/matches/{match_id}/status`. Sending `{"status":"contacted"}` immediately returns **409**. Sending `{"status":"saved"}` and then `{"status":"contacted"}` returns **200** for each request.
4. Call `DELETE /api/trackers/{tracker_id}`. Expect **204**. Call `GET /api/matches` and `GET /api/notifications` with empty filters to see empty lists. The post still appears in `GET /api/posts`. Calling `GET /api/trackers/{tracker_id}` for the deleted tracker returns **404**.

With the virtual environment active and PostgreSQL running, run the automated suite with `python -m pytest -q`. Tests use a separate database called `socialradar_test` (created automatically), so your real data is not touched. Expected result is **70 passed**.

To check persistence, create a tracker, stop the server, start it again, and call `GET /api/trackers`: the tracker is still there.
