"""
Executive Assistant Agent - Conversational AI with function calling
Connects Ollama ? Assistant Functions
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import ollama

from server.assistant_functions import FUNCTION_REGISTRY, execute_function

logger = logging.getLogger("agent")

class ExecutiveAgent:
    """JARVIS-style conversational agent with function calling"""
    
    def __init__(self, model: str = None):
        from server.config import get_config
        config = get_config()
        self.model = model or config.get("model", "qwen2.5:7b-instruct")
        self.conversation_history = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt with available functions"""
        functions_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in FUNCTION_REGISTRY.items()
        ])
        
        return f"""You are JARVIS, an advanced AI executive assistant. You are professional, proactive, and highly capable.

Your personality:
- Confident and efficient
- Anticipate user needs
- Provide actionable insights
- Always confirm before taking irreversible actions

Available functions:
{functions_desc}

Current date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

When you need to call a function:
1. Use the tool calling format provided by Ollama
2. Wait for the result before responding
3. Present results in a user-friendly way

Always be concise but thorough. If you need more information, ask."""

    def _build_tools_schema(self) -> List[Dict]:
        """Convert function registry to Ollama tools format"""
        tools = []
        
        for name, info in FUNCTION_REGISTRY.items():
            # Convert parameters to JSON schema
            properties = {}
            required = []
            
            for param_name, param_desc in info.get('parameters', {}).items():
                # Parse description for type hints
                param_type = "string"  # Default
                if "list" in param_desc.lower():
                    param_type = "array"
                elif "number" in param_desc.lower() or "minutes" in param_desc.lower():
                    param_type = "number"
                elif "dict" in param_desc.lower():
                    param_type = "object"
                
                properties[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }
                
                if "optional" not in param_desc.lower():
                    required.append(param_name)
            
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": info['description'],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })
        
        return tools

    async def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message and return response
        
        Returns:
            {
                "response": str,          # Agent's text response
                "tool_calls": [...],      # Functions called
                "tool_results": [...],    # Function results
                "thinking": str           # Agent's reasoning (optional)
            }
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Build messages for Ollama
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.conversation_history
            ]
            
            # Get tools schema
            tools = self._build_tools_schema()
            
            logger.info(f"Sending message to Ollama: {user_message}")
            
            # Call Ollama with function calling
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=tools
            )
            
            assistant_message = response['message']
            tool_calls = assistant_message.get('tool_calls', [])
            tool_results = []
            
            # Execute any function calls
            if tool_calls:
                logger.info(f"Agent wants to call {len(tool_calls)} functions")
                
                for tool_call in tool_calls:
                    func_name = tool_call['function']['name']
                    func_args = tool_call['function']['arguments']
                    
                    logger.info(f"Calling function: {func_name}({func_args})")
                    
                    # Execute function
                    result = await execute_function(func_name, func_args)
                    tool_results.append({
                        "function": func_name,
                        "arguments": func_args,
                        "result": result
                    })
                    
                    # Add tool result to conversation
                    messages.append(assistant_message)
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result)
                    })
                
                # Get final response after function execution
                logger.info("Getting final response after function execution")
                final_response = ollama.chat(
                    model=self.model,
                    messages=messages
                )
                
                final_message = final_response['message']['content']
            else:
                final_message = assistant_message.get('content', '')
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message
            })
            
            # Keep conversation history manageable (last 20 messages)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return {
                "response": final_message,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            return {
                "response": f"I encountered an error: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history reset")
