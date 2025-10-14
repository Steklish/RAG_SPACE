# local_generator.py

from datetime import date
import os
import json
import time
from typing import List, Type, TypeVar, Optional
import dotenv
import httpx
from pydantic import BaseModel, Field, ValidationError
import requests
from app.google_gen import GoogleGenAI
from app.llama_gen import LlamaGenAI
from app.qwen_gen import QwenGenAI
from app.schemas import *
from app.colors import *

# A Generic Type Variable for our generator's return type
T = TypeVar("T", bound=BaseModel)

RETRIES = int(os.getenv("LLAMACPP_MAX_RETRIES", 3))
TIMEOUT = int(os.getenv("LLAMACPP_TIMEOUT_S", 300))

class Generator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing a local Llama server to return a JSON object.
    """

    def __init__(self, base: str):
        """
        Initializes the generator with the local Llama server URL.
        """
            
        self.base = base
        
        self.url = f"{self.base}/v1/chat/completions"
        
        if os.getenv("USE_GEMINI") == '1':
            print(f"{INFO_COLOR}Using GEMINI model as LLM backend{Colors.RESET}")
            self.google_client = GoogleGenAI()
            self.complete_funtion =  self.google_client.complete
            self._backend_type = "gemini"
            self._get_model_from_server = self.google_client.get_model
        elif os.getenv("USE_QWEN") == '1':
            print(f"{INFO_COLOR}Using QWEN model as LLM backend{Colors.RESET}")
            self.qwen_client = QwenGenAI()
            self.complete_funtion = self.qwen_client.complete
            self._backend_type = "qwen"
            self._get_model_from_server = self.qwen_client.get_model
        else: 
            print(f"{INFO_COLOR}Using local Llama server as LLM backend{Colors.RESET}")
            self.llama_client = LlamaGenAI(base)
            self.complete_funtion = self.llama_client.complete
            self._backend_type = f"local <{self.base}>"
        
        print(f"{SUCCESS_COLOR}Generator instantiated successfully.{Colors.RESET}")
        self.model = self._get_model_from_server()
    

        
    def _clean_json_response(self, text_response: str) -> str:
        """
        Cleans the raw text response from the model to isolate the JSON object.
        """
        start_index = text_response.find("{")
        if start_index != -1:
            end_index = text_response.rfind("}")
            if end_index != -1:
                return text_response[start_index : end_index + 1]

        last_brace_open = text_response.rfind("{")
        if last_brace_open != -1:
            # Find the corresponding closing brace
            last_brace_close = text_response.rfind("}")
            if last_brace_close > last_brace_open:
                return text_response[last_brace_open : last_brace_close + 1]

        raise ValueError("No JSON object found in the response.")

    def generate_with_payload(self,
        payload: LLamaMessageHistory,
        pydantic_model: Type[T],
        system_prompt: Optional[str] = None,
        language: Optional[str] = None,
        retries: int = RETRIES,
        delay: int = 0,
    ) -> T:
        """
        Generates a Pydantic instance by asking the model for a JSON response.

        Args:
            pydantic_model: The Pydantic class to create an instance of.
        """    
        schema_json = json.dumps(pydantic_model.model_json_schema(), indent=2)

        language_instruction = ""
        if language:
            language_instruction = f"CRITICAL: All generated text content (like names, descriptions, effects, etc.) MUST be in the following language: {language}."

        system_prompt = f"""You are a JSON generation robot. Your sole purpose is to generate a single, valid JSON object that conforms to the provided JSON schema.

JSON Schema to follow:
```json
{schema_json}
```

Language Instruction:
{language_instruction}

Your response MUST be the raw JSON object, starting with `{{` and ending with `}}`.
DO NOT include any introductory text, explanations, apologies, or markdown code fences.
Your output will be directly parsed by a machine. Any character outside of the JSON object will cause a failure.
Begin your response immediately with the opening curly brace `{{`."""
        
        payload.messages.insert(0, SystemLamaMessage(role="system", content=system_prompt)) 
        payload.messages.append(UserLamaMessage(role="user", content="Based on our conversation, generate the JSON object now."))
        
        for i in range(retries):
            print(
                f"{HEADER_COLOR}Sending request to Local Llama Server{Colors.RESET} for: {ENTITY_COLOR}{pydantic_model.__name__}{Colors.RESET} (Language: {INFO_COLOR}{language or 'Default'}{Colors.RESET})"
            )
            try:
                print(f"{INFO_COLOR} url {self.url}:{Colors.RESET}")
                
                # response = requests.post(self.url, headers=headers, json=data)
                response_text = self.complete_funtion(
                    payload=payload,
                    temperature=0.7,
                    max_tokens=2048)
                
                    
                print(f"{SUCCESS_COLOR}Response received from Llama server.{Colors.RESET}")
                cleaned_response = self._clean_json_response(response_text)
                try:
                    parsed_data = json.loads(cleaned_response)
                    print(parsed_data)
                except json.JSONDecodeError as e:
                    print(f"{ERROR_COLOR}Error decoding JSON: {e}{Colors.RESET}")
                    print(f"{WARNING_COLOR}Cleaned Response that failed parsing:{Colors.RESET}")
                    print(cleaned_response)
                    raise e
                return pydantic_model(**parsed_data)
            except (requests.exceptions.RequestException, json.JSONDecodeError, ValidationError, ValueError) as e:
                print(
                    f"Error processing response (attempt {i + 1}/{retries}): {e}"
                )
                if i < retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise e
        raise Exception("Failed to generate object after multiple retries.")
        
        
    def generate_one_shot(
        self,
        pydantic_model: Type[T],
        prompt: Optional[str] = None,
        language: Optional[str] = None,
        retries: int = RETRIES,
        delay: int = 0,
        system_prompt: str = "",
        temperature: float = 0.7
    ) -> T:
        """
        Generates a Pydantic instance by asking the model for a JSON response.

        Args:
            pydantic_model: The Pydantic class to create an instance of.
            prompt: A specific description of the object to generate.
            language: The desired language for the generated text content (e.g., "Russian").
            retries: The number of times to retry the request if it fails.
            delay: The delay in seconds between retries.

        Returns:
            An instance of the specified Pydantic class.
        """
        schema_json = json.dumps(pydantic_model.model_json_schema(), indent=2)

        if prompt:
            user_request = f"Generate an object based on this description: '{prompt}'."
        else:
            user_request = "Generate a completely new, creative, and random object."

        language_instruction = ""
        if language:
            language_instruction = f"CRITICAL: All generated text content (like names, descriptions, effects, etc.) MUST be in the following language: {language}."

        # --- Construct the full prompt with the new language instruction ---
        full_prompt = f"""You are a JSON generation robot. Your sole purpose is to generate a single, valid JSON object that conforms to the provided JSON schema.

JSON Schema to follow:
```json
{schema_json}
```

User's request for the object's content:
{user_request}
{language_instruction}

Your response MUST be the raw JSON object, starting with `{{` and ending with `}}`.
DO NOT include any introductory text, explanations, apologies, or markdown code fences.
Your output will be directly parsed by a machine. Any character outside of the JSON object will cause a failure.
Begin your response immediately with the opening curly brace `{{`."""


        for i in range(retries):
            print(
                f"{HEADER_COLOR}Sending request to Local Llama Server{Colors.RESET} for: {ENTITY_COLOR}{pydantic_model.__name__}{Colors.RESET} (Language: {INFO_COLOR}{language or 'Default'}{Colors.RESET})"
            )
            try:
                print(f"{INFO_COLOR} url {self.url}:{Colors.RESET}")
                # response = requests.post(self.url, headers=headers, json=data)
                response_text = self.complete_funtion(
                    system_prompt=system_prompt,
                    user=full_prompt,
                    temperature=temperature,
                    max_tokens=2048)
                    
                print(f"{SUCCESS_COLOR}Response received from Llama server.{Colors.RESET}")
                cleaned_response = self._clean_json_response(response_text)
                try:
                    parsed_data = json.loads(cleaned_response)
                    print(parsed_data)
                except json.JSONDecodeError as e:
                    print(f"{ERROR_COLOR}Error decoding JSON: {e}{Colors.RESET}")
                    print(f"{WARNING_COLOR}Cleaned Response that failed parsing:{Colors.RESET}")
                    print(cleaned_response)
                    raise e
                return pydantic_model(**parsed_data)
            except (requests.exceptions.RequestException, json.JSONDecodeError, ValidationError, ValueError) as e:
                print(
                    f"Error processing response (attempt {i + 1}/{retries}): {e}"
                )
                if i < retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise e
        raise Exception("Failed to generate object after multiple retries.")
    
    def get_model_info(self):
        return self.model
        
    def _get_model_from_server(self):
        try:
            response = requests.get(f"{self.base}/v1/models", timeout=5)
            response.raise_for_status()
            models = response.json().get("data", [])
            if models:
                return models[0]["id"][models[0]["id"].rfind("\\") + 1:]
            return "No models found"
        except requests.exceptions.RequestException as e:
            print(f"Error fetching models from server: {e}")
            return "Not available"
        