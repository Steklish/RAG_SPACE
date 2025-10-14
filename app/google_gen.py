import os
from typing import Optional, List
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from app.colors import INFO_COLOR, Colors
from app.schemas import LLamaMessageHistory

# --- Main Class ---

class GoogleGenAI:
    def __init__(self):
        """
        Initializes the GoogleGenAI client.
        It's recommended to set the GEMINI_API_KEY environment variable.
        The client will automatically use it.
        """
        
        # Configure the API key. If the environment variable is set, this is not strictly
        # necessary as the library can find it automatically.
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(
            api_key=api_key,
        )
        
        self.model_name = os.getenv("GEMINI_MODEL")

    def get_model(self):
        return self.model_name
    
    def complete(self,
                 system_prompt: Optional[str] = None,
                 user: Optional[str] = None,
                 temperature: Optional[float] = 0.7,
                 max_tokens: Optional[int] = 1024,
                 payload: Optional[LLamaMessageHistory] = None) -> str:
        """
        Generates a response from the Gemini model.

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
        
        
        # Construct the conversation history
        contents = []
        if payload:
            # If a payload with history is provided, use it
            for message in payload.messages:
                if message.role == "system":
                    system_prompt = message.content  # Override system prompt if present
                    continue  # Skip system messages in the history
                role = "model" if (message.role == "assistant" or message.role == "model" or message.role == "agent") else message.role
                contents.append({'role': role, 'parts': [{'text': message.content}]})
        elif user:
            # If no payload, create a simple user prompt
            contents = [
                {'role': 'user', 'parts': [{'text': user}]}
                ]
        else:
            raise ValueError("Either 'user' prompt or 'payload' must be provided.")

        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=0.8,
            top_k=40,
            system_instruction=[
            genai.types.Part.from_text(text=system_prompt),
        ],
        )
        
        print("Contents sent to Gemini model:")
        try:
            text = ""
            print(f"{INFO_COLOR}Response from {self.__class__.__name__}:{Colors.RESET}")
            for chunk in self.client.models.generate_content_stream(
                model=self.model_name, # type: ignore
                contents=contents, # type: ignore
                config=generation_config,
            ):
                print(chunk.text, end="")
                if chunk.text: text += chunk.text
            with open("./storage/dev/response.txt", "a", encoding="utf-8") as f:
                f.write("\n" + "-" * 10)
                f.write(str(text))
                f.write("\n" + "-" * 10)
                
            print(f"Response from Gemini model: {text}")
            return text
        except Exception as e:
            # Basic error handling
            print(f"Error during Gemini model call: {e}")
            return f"An error occurred: {e}"

