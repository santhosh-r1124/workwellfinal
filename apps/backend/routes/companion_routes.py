from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

router = APIRouter(prefix="/api/companion", tags=["wellness-companion"])

client = Anthropic()

# Store conversation history per user
conversation_history = {}

class ChatMessage(BaseModel):
    email: str
    message: str

class WellnessContext(BaseModel):
    email: str
    stress_level: int = 5
    sleep_hours: float = 7
    mood_score: int = 5
    energy_level: int = 5
    work_hours: float = 8

def get_system_prompt(context: WellnessContext) -> str:
    """Generate system prompt with user context"""
    return f"""You are WorkWell, a compassionate mental wellness companion AI. Your role is to:
1. Provide mental health support (mindfulness, stress relief, emotional support)
2. Give work-life balance advice based on user data
3. Offer general health guidance (sleep, exercise, nutrition)
4. Provide personalized recommendations

Current User Context:
- Stress Level: {context.stress_level}/10
- Sleep Hours: {context.sleep_hours}
- Mood Score: {context.mood_score}/10
- Energy Level: {context.energy_level}/10
- Work Hours: {context.work_hours}

Provide warm, supportive, and actionable advice. Be empathetic and understanding.
Tailor recommendations to their current wellness state."""

@router.post("/chat")
async def chat_with_companion(msg: ChatMessage):
    """Send message to wellness companion"""
    try:
        user_email = msg.email
        user_message = msg.message

        # Initialize conversation history for user if not exists
        if user_email not in conversation_history:
            conversation_history[user_email] = []

        # Add user message to history
        conversation_history[user_email].append({
            "role": "user",
            "content": user_message
        })

        # Create system prompt (can be enhanced with actual user vitals)
        context = WellnessContext(email=user_email)
        system_prompt = get_system_prompt(context)

        # Get response from Claude
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=1024,
            system=system_prompt,
            messages=conversation_history[user_email]
        )

        assistant_message = response.content[0].text

        # Add assistant response to history
        conversation_history[user_email].append({
            "role": "assistant",
            "content": assistant_message
        })

        # Keep last 20 messages to avoid token overflow
        if len(conversation_history[user_email]) > 40:
            conversation_history[user_email] = conversation_history[user_email][-40:]

        return {
            "status": "success",
            "message": assistant_message,
            "email": user_email
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/history/{email}")
async def get_chat_history(email: str):
    """Get conversation history for a user"""
    if email not in conversation_history:
        return {"email": email, "messages": []}

    return {
        "email": email,
        "messages": conversation_history[email]
    }

@router.post("/wellness-plan")
async def generate_wellness_plan(context: WellnessContext):
    """Generate personalized wellness plan"""
    try:
        system_prompt = f"""You are a wellness coach. Based on the user's data, create a personalized wellness plan.

User Data:
- Stress Level: {context.stress_level}/10
- Sleep Hours: {context.sleep_hours}
- Mood Score: {context.mood_score}/10
- Energy Level: {context.energy_level}/10
- Work Hours: {context.work_hours}

Create a wellness plan with:
1. Key focus areas (3-4 areas)
2. Daily habits to adopt (3-5 recommendations)
3. This week's wellness goals (2-3 specific goals)
4. Resources/apps to use

Format as structured JSON."""

        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Create a wellness plan for {context.email}"
            }]
        )

        return {
            "status": "success",
            "email": context.email,
            "plan": response.content[0].text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation error: {str(e)}")

@router.delete("/history/{email}")
async def clear_chat_history(email: str):
    """Clear conversation history for a user"""
    if email in conversation_history:
        del conversation_history[email]

    return {"status": "success", "message": "History cleared"}
