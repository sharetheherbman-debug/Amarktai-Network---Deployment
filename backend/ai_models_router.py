"""
Multi-Model AI Router
Routes different tasks to appropriate AI models (gpt-4o, gpt-4, gpt-3.5-turbo)
"""
from openai import AsyncOpenAI
from logger_config import logger
from config import AI_MODELS
import os


class AIModelsRouter:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        # Map config model names to actual OpenAI models
        self.models = {
            'system_brain': 'gpt-4o',  # Best for strategic decisions
            'trade_decision': 'gpt-4o',  # Best for trading
            'reporting': 'gpt-4',  # Good for reports
            'chatops': 'gpt-4o'  # Best for chat
        }
    
    async def system_brain_decision(self, prompt: str, context: dict) -> str:
        """
        GPT-4o - System Brain
        For: Autopilot decisions, risk management, strategic planning
        """
        try:
            if not self.client:
                return "OpenAI API key not configured"
                
            system_message = f"""You are the Amarktai System Brain - the highest-level AI controller.

Your role: Make strategic decisions about autopilot, capital allocation, risk management.

Current system state:
{context}

Think strategically. Consider long-term growth, risk mitigation, and optimal capital deployment."""

            response = await self.client.chat.completions.create(
                model=self.models['system_brain'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"System brain error: {e}")
            # Fallback to trade decision
            return await self.trade_decision(prompt, context)
    
    async def trade_decision(self, prompt: str, context: dict) -> str:
        """
        GPT-4o - Trade Execution Brain
        For: Individual bot trading decisions, technical analysis
        """
        try:
            if not self.client:
                return "OpenAI API key not configured"
                
            system_message = f"""You are the Amarktai Trade Execution Brain.

Your role: Make fast, accurate trading decisions for individual bots.

Context:
{context}

Focus on: Technical patterns, entry/exit timing, position sizing."""

            response = await self.client.chat.completions.create(
                model=self.models['trade_decision'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Trade decision error: {e}")
            return f"Trade decision unavailable: {str(e)}"
    
    async def generate_report(self, prompt: str, data: dict) -> str:
        """
        GPT-4 - Reporting Brain
        For: Daily summaries, performance reports, email content
        """
        try:
            if not self.client:
                return "OpenAI API key not configured"
                
            system_message = f"""You are the Amarktai Reporting Brain.

Your role: Generate clear, concise reports and summaries.

Data to summarize:
{data}

Focus on: Key metrics, insights, actionable recommendations."""

            response = await self.client.chat.completions.create(
                model=self.models['reporting'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return f"Report generation unavailable: {str(e)}"
    
    async def chatops_response(self, prompt: str, context: dict, user_id: str) -> str:
        """
        GPT-4o - ChatOps Brain
        For: Dashboard chat, real-time commands, user interaction
        """
        try:
            if not self.client:
                return "OpenAI API key not configured"
                
            system_message = f"""You are the Amarktai ChatOps Brain - real-time assistant.

Your role: Respond quickly to user queries and execute commands.

System context:
{context}

Be: Fast, accurate, helpful. Execute commands when requested."""

            response = await self.client.chat.completions.create(
                model=self.models['chatops'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"ChatOps error: {e}")
            return f"ChatOps unavailable: {str(e)}"
    
    def route_to_best_model(self, task_type: str) -> str:
        """Determine which model to use for a task"""
        routing_map = {
            "autopilot": "system_brain",
            "risk_assessment": "system_brain",
            "capital_allocation": "system_brain",
            "strategic_planning": "system_brain",
            "trade_execution": "trade_decision",
            "technical_analysis": "trade_decision",
            "bot_decision": "trade_decision",
            "daily_report": "reporting",
            "summary": "reporting",
            "email": "reporting",
            "chat": "chatops",
            "command": "chatops",
            "question": "chatops"
        }
        
        model_type = routing_map.get(task_type, "chatops")
        return self.models[model_type]


ai_models_router = AIModelsRouter()
