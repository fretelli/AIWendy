# TODO Report

**Total items:** 4

## Feature (4 items)

### keeltrader\apps\api\routers\chat.py:835
**Type:** `TODO`
**Description:** Implement session listing with pagination

**Details:**
```
- Query ChatSession table: SELECT * FROM chat_sessions WHERE user_id = ?
- Add pagination params: skip, limit (default 20)
- Order by updated_at DESC
- Include message count and last message preview
- Return SessionListResponse with total count
Placeholder endpoint - returns empty list
```

### keeltrader\apps\api\routers\chat.py:852
**Type:** `TODO`
**Description:** Implement session retrieval with messages

**Details:**
```
- Query ChatSession by id and verify user_id matches current_user
- Load related ChatMessage records ordered by created_at
- Return 404 if session not found or doesn't belong to user
- Include coach info and session metadata
Placeholder endpoint - returns empty session
```

### keeltrader\apps\api\routers\coaches.py:258
**Type:** `TODO`
**Description:** Implement subscription-based coach filtering

**Details:**
```
- Add subscription_tier field to User model (free/premium/elite)
- Filter coaches based on user.subscription_tier >= coach.required_tier
- Return 403 if user tries to access premium coach without subscription
Currently all coaches are available to all users
```

### keeltrader\apps\api\routers\users.py:58
**Type:** `TODO`
**Description:** Implement user profile update

**Details:**
```
- Create UserUpdateRequest schema (name, email, timezone, locale, etc.)
- Validate email uniqueness if changed
- Hash password if password field is provided
- Update user record in database
- Return updated UserResponse
Placeholder endpoint
```
