# Restaurant Management System — Full Project Documentation

## Overview
A full-stack backend for a Restaurant Management System (RMS) built with Django and Django REST Framework (DRF). It supports customer flows (discovery, reservations, ordering), staff flows (waiters, chefs, managers), an admin layer with role-based access control, and AI-powered features (menu recommendations, sentiment analysis, upsell, semantic search, wait-time prediction, and chat sessions) using Groq LLM APIs.

- Language: Python 3.11.9
- Frameworks: Django 5.2.4, DRF 3.16.0
- Auth: JWT (djangorestframework-simplejwt) with token versioning and blacklisting
- DB: SQLite (dev), PostgreSQL (prod-ready)
- Docs: Swagger/Redoc via drf-yasg
- Deployment: Procfile (Gunicorn + migrations + collectstatic)
- AI: Groq API (llama3-8b-8192), configured via environment variable `GROQ_API_KEY`

---

## Quick Start
1. Create and activate venv
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Environment
   - Create `.env` with at least:
     ```bash
     GROQ_API_KEY=your_key
     DEBUG=true
     ```
4. Migrate & run
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
5. API docs
   - http://localhost:8000/swagger/
   - http://localhost:8000/redoc/

---

## Project Structure
```
rms/                               # project root
├─ manage.py                       # Django CLI entrypoint
├─ requirements.txt                # Python dependencies
├─ Procfile                        # Deployment command (migrate + collectstatic + gunicorn)
├─ runtime.txt                     # Python runtime for deployment
├─ README.md                       # Basic project README
├─ STAFF_AUTH_README.md            # Staff auth system walkthrough
├─ RMS_API_Collection.json         # API collection (e.g., Postman)
├─ db.sqlite3                      # Dev database
├─ .env                            # Environment variables (not committed)
├─ templates/                      # Django templates
│  └─ admin/login.html             # Custom admin login
├─ staticfiles/                    # Collected static assets (prod)
│  └─ admin/, drf-yasg/, rest_framework/ ...
├─ .zencoder/rules/repo.md         # Repo metadata summary
├─ accounts/                       # Accounts (users, staff, auth)
├─ restaurants/                    # Restaurants, menu, reservations, reviews
├─ orders/                         # Orders and order items
├─ ai/                             # AI features (services, routes, models)
└─ rms/                            # Django project (settings, urls, wsgi, asgi)
```

---

## Core Project (rms/)
- `rms/settings.py`
  - INSTALLED_APPS: Django core, DRF, SimpleJWT, drf-yasg, corsheaders, and local apps
  - DB: SQLite in dev
  - Static/Media: WhiteNoise configured for static; MEDIA for uploads
  - REST_FRAMEWORK:
    - Default authentication: Versioned JWT + Session/Basic (for browsing)
    - Default permissions: IsAuthenticated
    - Scoped throttling: scope `ai` limited to `20/min`
  - SIMPLE_JWT: token lifetime, blacklist, HS256 signing, header type Bearer
  - CORS: permissive in dev; custom origins included
  - Custom user model: `accounts.User`

- `rms/urls.py`
  - Routes:
    - `/api/accounts/` → `accounts.urls`
    - `/api/restaurants/` → `restaurants.urls`
    - `/api/orders/` → `orders.urls`
    - `/api/ai/` → `ai.urls`
  - JWT endpoints: token obtain/refresh/verify
  - Swagger/Redoc: `/swagger/`, `/redoc/` and `/swagger.json`
  - Admin routing: default admin + superadmin/manager/staff admin sites (from restaurants.admin)

- `rms/wsgi.py`, `rms/asgi.py`: Standard Django entrypoints for deployment.

---

## Accounts App (accounts/)
Responsible for user management, staff management, phone verification, password reset, JWT customization, admin access routing, and permission controls.

### Key Files
- `models.py`
  - `User(AbstractUser)`: uses `phone` as USERNAME_FIELD; flags: `is_customer`, `is_staff_member`, `is_phone_verified`.
  - `PhoneVerification`: 4-digit codes, 10-min expiry for phone verification.
  - `CustomerProfile`: image + optional allergies/diet/preferences/address (free-text).
  - `StaffProfile`: role (`waiter`, `chef`, `manager`, `employee`), image, restaurant link, `is_on_shift`.
  - `StaffShift`: staff schedule; keeps `is_on_shift` up to date.
  - `PasswordReset`: 4-digit code, 10-min expiry for password resets.
  - `TokenVersion`: per-user token version, used to invalidate tokens post-logout.

- `serializers.py`
  - Token serializer adds custom claims (`phone`, `is_customer`, `is_staff_member`, and `token_version`).
  - Validation serializers for phone verification, registration, login, password reset flows.
  - Profile serializers for customer/staff.
  - `StaffLoginSerializer` to validate staff login.

- `views.py`
  - Public (AllowAny): send/verify phone code, register, login, forgot/verify/reset password.
  - Authenticated: logout (blacklists the single token), profile fetch/update, staff login/logout/profile/shifts, create staff/shift, list staff, debug endpoints.

- `urls.py`
  - `/send-verification-code/`, `/verify-phone/`
  - `/register/`, `/login/`, `/logout/`
  - `/forgot-password/`, `/verify-reset-code/`, `/reset-password/`
  - `/profile/`, `/profile/update/`, `/profile/upload-image/`
  - Staff: `/staff/login/`, `/staff/logout/`, `/staff/profile/`, `/staff/profile/update/`, `/staff/shifts/`, `/staff/clock-toggle/`
  - Manager: `/staff/create/`, `/staff/create-waiter/`, `/staff/create-chef/`, `/staff/shifts/create/`, `/staff/list/`

- `authentication.py`
  - `VersionedJWTAuthentication`: rejects blacklisted tokens and tokens with stale `token_version`.

- `middleware.py`
  - `AdminAccessMiddleware`: routes users to appropriate admin site based on role; enforces access restrictions to `/superadmin/`, `/manager/`, and `/staff/`.

- `permissions.py`
  - Custom DRF permissions for role-based access (e.g., `IsRestaurantManager`, `IsWaiterOrChef`).

- `management/commands/`
  - `init_admin.py`: initialize default admin user(s) (typical)
  - `create_test_staff.py`: seed test staff for a restaurant
  - `seed_data.py`: seed core data
  - `update_staff_permissions.py`: maintenance for staff permissions

### Data Flow
- Registration: verify phone → register user → create profile → JWT issued with version claim.
- Login: returns JWT + user profile details.
- Logout: blacklists current token and invalidates via token version checks.

---

## Restaurants App (restaurants/)
Manages restaurants, categories, images, menu items, tables, reservations, reservation status updates, and reviews.

### Key Files
- `models.py`
  - `Category`: cuisine type/categories
  - `Restaurant`: core info + services (dine-in/takeaway/delivery) + rating
  - `RestaurantImage`: gallery
  - `MenuItem`: per-restaurant item with dietary flags, price, prep time
  - `Table`: per-restaurant seating capacity
  - `Reservation`: reservation details with status
  - `ReservationStatusUpdate`: track status changes (e.g., notifications)
  - `Review`: user reviews (rating 1–5 + comment)

- `views.py`
  - Public:
    - `restaurant_list`, `category_list`, `restaurant_detail`, `restaurant_menu`, `restaurant_reviews`
  - Authenticated customer/staff:
    - `available_tables`, `create_reservation`, `user_reservations`, `reservation_detail`, `cancel_reservation`, `update_reservation_status`
  - Additional helpers for available dates/times/durations and dashboards.

- `urls.py`
  - `/` (list), `/categories/`, `/<id>/`, `/<id>/menu/`, `/<id>/reviews/`
  - `/<id>/tables/`, `/<id>/reserve/`
  - `/reservations/`, `/reservations/<id>/`, `/reservations/<id>/cancel/`, `/reservations/<id>/update-status/`
  - `/<id>/available-dates|times|durations/`

- `admin.py`
  - Defines role-focused admin sites referenced in `rms/urls.py`: `superadmin_site`, `manager_site`, `staff_site` (as imported in project urls).

### Reservation Availability Logic
- `available_tables` filters tables by capacity and excludes those already reserved for a given time/date.
- Staff-only and role-specific endpoints guard protected operations.

---

## Orders App (orders/)
Handles order lifecycle for dine-in, pickup, and delivery.

### Key Files
- `models.py`
  - `Order`: core order entity with type, status, payment info, optional reservation link, estimated prep time.
  - `OrderItem`: menu item lines with quantity and special instructions.
  - `OrderStatusUpdate`: audit trail for status changes and notification messages.

- `views.py`
  - Customers: list orders, create order, order detail, cancel, track status.
  - Staff: staff order list, staff update order, chef orders, waiter orders.
  - Business rules: checks that staff belong to a restaurant; chefs cannot create orders.

- `urls.py`
  - `/` (customer orders), `/create/`, `/<id>/`, `/<id>/cancel/`, `/<id>/track/`
  - Staff: `/staff/`, `/staff/<id>/update/`, `/chef/orders/`, `/waiter/orders/`

### Prep Time Estimation
- `Order.calculate_preparation_time()`: computes max per-item prep time scaled by quantity to set overall estimate.

---

## AI App (ai/)
Adds AI-powered features on top of the operational data.

### Key Files
- `services.py`
  - Uses Groq client with `llama3-8b-8192`.
  - Methods:
    - `chat(message, user, context)`: general assistant with optional contextual info.
    - `get_menu_recommendations(restaurant_id, dietary_preferences, allergies, budget_range, preferences, cuisine_type)`: returns an array of dish recommendations as JSON.
    - `get_reservation_suggestions(restaurant_id, party_size, preferred_date, preferred_time, special_occasion)`: returns time suggestions and tips as JSON.
    - `analyze_sentiment(text, context)`: returns sentiment, confidence, and emotion breakdown; resilient JSON parsing.
    - `get_basic_recommendations(user_id, recommendation_type, location, preferences)`: returns general recommendations as JSON.
    - New:
      - `semantic_menu_search(query, restaurant_id)`: semantic-like top-5 menu item matches with reasons and scores.
      - `upsell_recommendations(order_id)`: top-3 complementary items for an order.
      - `reviews_summarize(restaurant_id, since)`: summary/themes/pros/cons/action items.
      - `predict_wait_time(restaurant_id, party_size, time)`: returns estimate, range, confidence, and tips.

- `views.py`
  - Uses DRF with request serializers, scoped throttling (`ai`), and caching.
  - Endpoints:
    - `POST /api/ai/chat/` — chat; supports `session_id`; persists messages.
    - `POST /api/ai/menu-recommendations/`
    - `POST /api/ai/reservation-suggestions/`
    - `POST /api/ai/sentiment-analysis/`
    - `POST /api/ai/basic-recommendations/`
    - New:
      - `POST /api/ai/menu/search/semantic/`
      - `POST /api/ai/orders/upsell/`
      - `POST /api/ai/reviews/summarize/`
      - `POST /api/ai/reservations/predict-wait/`
      - `POST /api/ai/chat/start-session/`
      - `GET|POST /api/ai/chat/{session_id}/messages/`

- `serializers.py`
  - Validation for all AI endpoints: Chat, MenuRecommendations, ReservationSuggestions, Sentiment, BasicRecommendations, SemanticMenuSearch, UpsellRecommendations, ReviewsSummarize, PredictWaitTime.

- `models.py`
  - `ChatSession`: per-user chat sessions (UUID primary key) with optional restaurant/topic.
  - `ChatMessage`: message history with roles (user/assistant/system).
  - `ReviewAnalysis`: stores analysis results of a review (sentiment/emotions/summary/suggestions).
  - `RecommendationLog`: audit of recommendations with input/output and acceptance tracking.
  - New:
    - `TableSelectionLog`: one-to-one with Reservation; captures selection method, selected table, available tables, AI reasoning, confidence, performance metrics.

- `urls.py`
  - Wires all endpoints under `/api/ai/`.

### AI Design Notes
- Strict JSON-only responses with robust fallback parsing.
- Caching on read-heavy recommendations to reduce token usage.
- Throttling to protect cost and abuse.
- Session-based chat with short conversation history fed as context.

### AI Usage Examples (cURL)
1) Chat with session
```bash
curl -X POST http://localhost:8000/api/ai/chat/start-session/ \
  -H "Authorization: Bearer $TOKEN"
# -> {"session_id":"<uuid>"}

curl -X POST http://localhost:8000/api/ai/chat/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"Suggest spicy mains","session_id":"<uuid>"}'
```

2) Menu recommendations
```bash
curl -X POST http://localhost:8000/api/ai/menu-recommendations/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"restaurant_id":1,"dietary_preferences":["vegetarian"],"budget_range":"low"}'
```

3) Semantic menu search
```bash
curl -X POST http://localhost:8000/api/ai/menu/search/semantic/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"creamy mushroom pasta","restaurant_id":1}'
```

4) Upsell for order
```bash
curl -X POST http://localhost:8000/api/ai/orders/upsell/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"order_id":123}'
```

5) Reviews summarize
```bash
curl -X POST http://localhost:8000/api/ai/reviews/summarize/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"restaurant_id":1,"since":"2024-07-01"}'
```

6) Predict wait time
```bash
curl -X POST http://localhost:8000/api/ai/reservations/predict-wait/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"restaurant_id":1,"party_size":4,"time":"19:30:00"}'
```

---

## Templates and Static
- `templates/admin/login.html`: overrides default admin login template.
- `staticfiles/`: collected assets used in production. WhiteNoise is configured in settings.

---

## Root Files
- `manage.py`: standard Django entrypoint.
- `requirements.txt`: dependencies (Django, DRF, JWT, drf-yasg, corsheaders, channels, redis, celery, pillow, twilio, stripe, groq, firebase-admin, etc.).
- `Procfile`: `web: python manage.py migrate && python manage.py collectstatic --no-input && gunicorn rms.wsgi`
- `runtime.txt`: `python-3.11.9`
- `README.md`: quick setup and endpoint overview.
- `STAFF_AUTH_README.md`: extensive staff authentication and role documentation.
- `.zencoder/rules/repo.md`: auto-generated repo meta used by tooling.
- `RMS_API_Collection.json`: likely a Postman/Insomnia collection for API testing.
- `firebase_service.py`: Firebase Admin SDK integration for FCM notifications.
- Note: a stray file `h origin main` is present in root; it appears to be accidental and can be removed safely.

---

## Authentication & Security
- JWT via `djangorestframework-simplejwt`.
- Custom `VersionedJWTAuthentication`:
  - Enforces that JWT includes `token_version` matching `TokenVersion` in DB.
  - Checks token blacklist (OutstandingToken + BlacklistedToken) to block reused tokens after logout.
- Admin access protection via `AdminAccessMiddleware`:
  - Redirects authenticated users from `/admin/` to role-specific sites.
  - Guards `/superadmin/` (superusers only), `/manager/` (manager staff only), `/staff/` (waiters/chefs only).
- DRF throttling for AI scope (`ai`: 20/min) and caching for expensive AI reads.
- CORS enabled for dev; restrict origins in production.

### Admin Sites and Permissions
- Separate admin sites in `restaurants/admin.py`:
  - `superadmin_site`: full Django admin for superusers.
  - `manager_site`: limited admin for managers; auto-grants CRUD perms on MenuItem/Category/Table/Reservation/Orders.
  - `staff_site`: limited admin for waiters/chefs; auto-grants view/change/add/delete on Table/Reservation/Order/Review.
- Helper `ensure_user_permissions(user, model_classes)` ensures required perms exist on login.

---

## Database Models (Summary)
- Accounts: `User`, `CustomerProfile`, `StaffProfile`, `StaffShift`, `PhoneVerification`, `PasswordReset`, `TokenVersion`.
- Restaurants: `Category`, `Restaurant`, `RestaurantImage`, `MenuItem`, `Table`, `Reservation`, `ReservationStatusUpdate`, `Review`.
- Orders: `Order`, `OrderItem`, `OrderStatusUpdate`.
- AI: `ChatSession`, `ChatMessage`, `ReviewAnalysis`, `RecommendationLog`, `TableSelectionLog`.
- Notifications: `FCMToken`, `NotificationTemplate`, `NotificationLog`, `TopicSubscription`.

### Accounts Models — Field-level Details
- `User`
  - Replaces username with `phone` (unique), keeps `email` optional.
  - Flags: `is_customer`, `is_staff_member`, `is_phone_verified`; ensures `is_staff=True` if staff member.
  - Authentication uses phone + password.
- `PhoneVerification`
  - `phone`, 4-digit `code`, `is_used`, `created_at` with 10-min expiry; APIs: `generate_code`, `verify_code`.
- `CustomerProfile`
  - `profile_image`, free-text `allergies`, `dietary_preferences`, `default_address`; `created_at`, `updated_at`.
- `StaffProfile`
  - `role` in ['waiter','chef','manager','employee'], `restaurant` FK, `is_on_shift`, timestamps.
- `StaffShift`
  - `staff` FK, `start_time`, `end_time`, `is_active`, `created_by`; save() toggles `staff.is_on_shift` based on now.
- `PasswordReset`
  - 4-digit code with 10-min expiry; APIs: `generate_code`, `verify_code`.
- `TokenVersion`
  - `version` int; methods `get_version`, `increment_version` used to invalidate JWTs.

### Restaurants Models — Field-level Details
- `Category`
  - `name`, optional `image`, `description`, `is_active`, timestamps.
- `Restaurant`
  - Core info + images + `opening_time`/`closing_time`, `categories` M2M, service flags, `average_rating` decimal.
- `RestaurantImage`
  - `restaurant` FK, `image`, `caption`, `is_active`, created timestamp.
- `MenuItem`
  - `restaurant` FK, `name`, `description`, `price`, `image`, `food_category` FK, dietary flags, `preparation_time`, activity flags.
- `Table`
  - `restaurant` FK, `table_number`, `capacity`, `is_active`, `is_reserved`.
- `Reservation`
  - FKs to `customer`, `restaurant`, `table`; `party_size`, `reservation_date`/`time`, `duration_hours`, `status`, `special_requests`, timestamps.
- `ReservationStatusUpdate`
  - FK to `reservation`, `status`, `notes`, `updated_by`, `created_at`, `is_notified`.
- `Review`
  - FK to `customer` and `restaurant`, `rating` 1–5, optional `comment`, timestamps.

### Orders Models — Field-level Details
- `Order`
  - FKs to `customer`, `restaurant`, optional `reservation`.
  - `order_type` in ['dine_in','pickup','delivery']; `status` lifecycle; timestamps and `estimated_preparation_time`.
  - Payment: `subtotal`, `tax`, `delivery_fee`, `total`, `payment_status`, `payment_method`, optional `delivery_address`.
  - Assignment: `assigned_chef`, `assigned_waiter`.
  - Helpers: `calculate_total()`, `calculate_preparation_time()` (max of item prep times x quantity).
- `OrderItem`
  - FK to `order` and `menu_item`, `quantity`, `item_price`, optional `special_instructions`; computed `item_total`.
- `OrderStatusUpdate`
  - FK to `order`, `status`, `notes`, `updated_by`, `created_at`, `notification_message`, `is_notified`.

### AI Models — Field-level Details
- `ChatSession`
  - UUID `id`, `user` FK, optional `restaurant`, `topic`, timestamps.
- `ChatMessage`
  - FK to `session`, `role` in ['user','assistant','system'], `content`, `created_at`.
- `ReviewAnalysis`
  - `review` one-to-one, `sentiment`, `confidence`, `emotions` JSON, `summary`, `suggestions` JSON, `created_at`.
- `RecommendationLog`
  - `user` FK, `context` in ['menu','upsell','semantic','basic','chat'], `input_payload` JSON, `output` JSON, `accepted`, `created_at`.

---

## API Endpoints (High-Level)
- Accounts: authentication, phone verification, password reset, profile management, staff login/profile/shifts, and manager staff actions.
- Restaurants: listing, categories, details, menu, reviews, tables availability, reservation CRUD.
- Orders: CRUD-like order operations for customers and staff, status tracking.
- Notifications: FCM token register/update, templates CRUD + test, logs read, topic subscribe/unsubscribe, admin broadcast.
- AI: chat sessions/messages, menu recommendations, reservation suggestions, sentiment analysis, basic recommendations, semantic search, upsell, review summaries, wait-time prediction.

See Swagger at `/swagger/` for request/response schemas and try-it-out.

---

## Deployment
- Procfile ensures:
  1) migrate DB
  2) collect static assets (WhiteNoise)
  3) run Gunicorn with `rms.wsgi`
- Environment variables (typical):
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `DATABASE_URL` (for Postgres via dj-database-url, if adopted)
  - `GROQ_API_KEY`
  - `FIREBASE_SERVICE_ACCOUNT_KEY` (JSON string) or `FIREBASE_SERVICE_ACCOUNT_PATH` (file path) for FCM
- Switch DB to Postgres in production (uncomment psycopg2 in requirements and configure `DATABASES`).
- Consider `django-redis` for cache backend in production.
- Static files already collected to `staticfiles/`; ensure WhiteNoise middleware is active in settings.

---

## Testing
- `pytest` and `pytest-django` are included; basic tests can be added per app under `tests.py` or `/tests/` packages.
- Example:
  ```bash
  pytest -q
  ```

---

## AI Configuration
- Environment: `GROQ_API_KEY` in `.env`.
- Model: `llama3-8b-8192` (fast/efficient). You can parameterize this via settings if needed.
- Cost control: endpoint throttling, caching, strict JSON schemas.

---

## Future Enhancements
- Switch dev free-text preferences to structured JSON (`CustomerPreference`) for stronger personalization.
- Postgres + pgvector for true semantic search on menu items.
- Signals to auto-analyze new reviews and store `ReviewAnalysis`.
- Track recommendation acceptance into `RecommendationLog`.
- Celery for asynchronous heavy AI tasks (fire-and-poll pattern).

---

## Maintenance Tips
- Prune `staticfiles/` when changing static pipeline; run `collectstatic` in clean state.
- Regularly rotate `SECRET_KEY` for production and use environment variables.
- Tighten CORS in production.
- Protect admin endpoints with strong passwords and 2FA if possible.
- Periodically run management commands:
  - `python manage.py init_admin --password <pw>`: ensure superuser exists.
  - `python manage.py create_test_staff --restaurant-id <id>`: seed staff for a restaurant.
  - `python manage.py update_staff_permissions`: re-grant perms based on roles.
  - `python manage.py seed_data [--preserve-users]`: generate demo data.

---

## File-by-File Index (Essentials)
- Project: `rms/settings.py`, `rms/urls.py`, `rms/wsgi.py`, `rms/asgi.py`
- Accounts: `accounts/models.py`, `accounts/views.py`, `accounts/urls.py`, `accounts/serializers.py`, `accounts/authentication.py`, `accounts/middleware.py`, `accounts/permissions.py`, `accounts/management/commands/*`
- Restaurants: `restaurants/models.py`, `restaurants/views.py`, `restaurants/urls.py`, `restaurants/admin.py`
- Orders: `orders/models.py`, `orders/views.py`, `orders/urls.py`
- AI: `ai/services.py`, `ai/views.py`, `ai/serializers.py`, `ai/models.py`, `ai/urls.py`
- Templates/Static: `templates/admin/login.html`, `staticfiles/*`
- Root: `manage.py`, `requirements.txt`, `Procfile`, `runtime.txt`, `README.md`, `STAFF_AUTH_README.md`, `.zencoder/rules/repo.md`, `.env (local only)`

This documentation should give you a complete understanding of what each file and module does, how the pieces connect, and how to run, extend, and deploy the system. If you want this split into multiple topic-specific docs (e.g., AI-only, Auth-only), I can generate them next.