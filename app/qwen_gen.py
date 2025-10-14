import os
import json
import requests
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas import LLamaMessageHistory
from app.colors import *


class QwenGenAI:
    def __init__(self):
        """
        Initializes the QwenGenAI client.
        It's recommended to set the QWEN_TOKEN environment variable.
        """
        api_key = os.getenv("QWEN_TOKEN")

        if not api_key:
            raise ValueError("QWEN_TOKEN environment variable not set.")
        
        self.api_key = api_key
        self.model_name = os.getenv("QWEN_MODEL_OPENROUTER")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def get_model(self):
        return self.model_name
    
    def complete(self,
                 system_prompt: Optional[str] = None,
                 user: Optional[str] = None,
                 temperature: Optional[float] = 0.7,
                 max_tokens: Optional[int] = 1024,
                 payload: Optional[LLamaMessageHistory] = None) -> str:
        """
        Generates a response from the Qwen model via OpenRouter API.

        Args:
            system_prompt: The system instruction or context.
            user: The user's prompt (used if payload is not provided).
            temperature: The sampling temperature.
            max_tokens: The maximum number of tokens to generate.
            payload: A message history object.

        Returns:
            The generated text response from the model.
        """
        system_prompt = system_prompt or ""
        
        # Construct the messages list
        messages = []
        
        if payload:
            # If a payload with history is provided, use it
            for message in payload.messages:
                if message.role == "system":
                    system_prompt = message.content  # Override system prompt if present
                    continue  # Skip system messages in the messages list
                role = "assistant" if (message.role == "model" or message.role == "agent") else message.role
                messages.append({'role': role, 'content': message.content})
        
        elif user:
            # If no payload, create a simple user prompt
            messages = [
                {'role': 'user', 'content': user}
            ]
        else:
            raise ValueError("Either 'user' prompt or 'payload' must be provided.")

        # Add system prompt if it exists
        if system_prompt:
            messages.insert(0, {'role': 'system', 'content': system_prompt})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        print("Messages sent to Qwen model:")
        print(json.dumps(messages, indent=2))
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the content from the response
            content = result['choices'][0]['message']['content']
            
            print(f"{INFO_COLOR}Response from {self.__class__.__name__}:{Colors.RESET} {content}")
            
            # Write response to file for debugging
            with open("./storage/dev/response.txt", "a", encoding="utf-8") as f:
                f.write("\n" + "-" * 10)
                f.write(str(content))
                f.write("\n" + "-" * 10)
            
            return content
        except requests.exceptions.RequestException as e:
            print(f"{ERROR_COLOR}Error during Qwen model API call: {e}{Colors.RESET}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status code: {e.response.status_code}")
                try:
                    error_detail = e.response.json()
                    print(f"Error details: {error_detail}")
                except:
                    print(f"Response text: {e.response.text}")
            return f"An error occurred: {e}"
        except Exception as e:
            print(f"{ERROR_COLOR}Unexpected error during Qwen model call: {e}{Colors.RESET}")
            return f"An unexpected error occurred: {e}"