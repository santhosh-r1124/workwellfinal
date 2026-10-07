# WorkWell AI - Integration Plan

## 1. CSV Data Import
- **Method**: Local file upload via UI
- **Location**: `/admin/import-csv` or management portal
- **File Format**: TSV (tab-separated) with trainee telemetry data
- **Fields**: trainee_id, email, date, stress_level, sleep_hours, mood_score, etc.

## 2. Google Calendar Integration
- **Purpose**: Extract complete calendar analytics
- **Data to Extract**:
  - Work hours/meetings (start, end, duration)
  - Free/busy status for availability tracking
  - Meeting titles/types (1:1, team, client, standup, etc.)
  - Calendar analytics for workload insights

**Implementation**:
- OAuth 2.0 setup for Google Calendar API
- Backend endpoint: `GET /api/calendar/events?email={trainee_email}`
- Sync meeting data into `CalendarEvent` table
- Calculate: meetings_per_day, total_meeting_hours, meeting_types

## 3. Companion LLM API
- **Purpose**: Mental wellness chatbot
- **Features**:
  - Mental wellness support (mindfulness, stress relief, emotional support)
  - Work-life balance advice (based on vitals + calendar)
  - General health assistant (sleep, exercise, nutrition)
  - Personalized recommendations

**Endpoints**:
- `POST /api/chat` - Send message to wellness chatbot
- `GET /api/chat/history?email={email}` - Get conversation history
- `POST /api/wellness-plan` - Generate personalized wellness plan

**LLM Integration**:
- Use Claude API for wellness chatbot
- Context: user vitals, calendar events, stress levels
- Response: supportive, actionable wellness advice

## Database Schema Additions
```sql
-- Calendar Events
CREATE TABLE calendar_events (
  id UUID PRIMARY KEY,
  user_email VARCHAR,
  event_title VARCHAR,
  event_type VARCHAR,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  duration_minutes INT,
  is_free_time BOOLEAN
);

-- Chat Messages
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY,
  user_email VARCHAR,
  message TEXT,
  role VARCHAR (user/assistant),
  created_at TIMESTAMP
);

-- Wellness Plans
CREATE TABLE wellness_plans (
  id UUID PRIMARY KEY,
  user_email VARCHAR,
  plan_date DATE,
  recommendations TEXT[],
  focus_areas TEXT[]
);
```

## Implementation Priority
1. ✅ CSV data import (create UI + backend endpoint)
2. 🔄 Google Calendar OAuth setup
3. 🔄 Calendar sync backend
4. 🔄 LLM companion API endpoint
5. 🔄 Frontend chatbot UI

## API Keys Needed
- Google Calendar API key
- Claude API key (already configured?)

