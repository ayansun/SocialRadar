# SocialRadar

SocialRadar is a FastAPI project for Web Programming Fundamentals. It helps freelancers find potential clients by matching social media posts against keyword trackers. Add Bluesky and Threads posts manually or load sample posts with `POST /api/demo/seed`. Data lives in memory and resets when the server restarts.

## Run locally

From the project directory, with Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app
```

The same server hosts the [web app](http://127.0.0.1:8000/) and [Swagger UI](http://127.0.0.1:8000/docs).

## Workflows

1. **Manage trackers.** Create, edit, pause, or delete a tracker. Each tracker has a unique name, at least one keyword, and at least one platform. Creating or editing a tracker rechecks stored posts.
2. **Match posts.** The service checks active trackers for the post's platform. It matches phrases without regard to case, skips posts with excluded phrases, and creates one lead and one notification per matching tracker. Reusing an `external_id` on the same platform returns HTTP 409.
3. **Work through leads.** A new lead can be saved or dismissed. A saved lead can be marked as contacted or dismissed, a contacted lead can be dismissed, and a dismissed lead can be restored to new. Notifications can be marked as read or unread. Deleting a tracker or post removes its leads and their notifications.

## Project structure

- [`app/main.py`](app/main.py) configures FastAPI, registers routers, and handles application errors.
- [`app/api/`](app/api/) defines routes, [`app/schemas/`](app/schemas/) defines Pydantic models, and [`app/services/`](app/services/) implements business rules.
- [`app/storage.py`](app/storage.py) stores trackers, posts, leads, and notifications in Python dictionaries linked by IDs.
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

With the virtual environment active, run the automated suite with `python -m pytest -q`. Expected result is **60 passed**.
