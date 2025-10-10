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
from app.schemas import *
from app.colors import *

# A Generic Type Variable for our generator's return type
T = TypeVar("T", bound=BaseModel)

RETRIES = int(os.getenv("LLAMACPP_MAX_RETRIES", 3))
TIMEOUT = int(os.getenv("LLAMACPP_TIMEOUT_S", 300))

class LocalGenerator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing a local Llama server to return a JSON object.
    """

    def __init__(self, base: str):
        """
        Initializes the generator with the local Llama server URL.
        """
        self.base = base
        self.model = self._get_model_from_server()
        self.url = f"{self.base}/v1/chat/completions"
        print(f"{SUCCESS_COLOR}LocalGenerator instantiated successfully.{Colors.RESET}")
    
    def _payload(self, system_prompt: str, user: str, temperature: Optional[float], max_tokens: Optional[int], grammar: Optional[str] = None):
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": user or ""},
            ],
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if grammar is not None:
            body["grammar"] = grammar
        return body
    
    def complete(self, 
                 system_prompt: Optional[str] = None, 
                 user: Optional[str] = None, 
                 temperature: Optional[float] = None, 
                 max_tokens: Optional[int] = None,
                 payload: Optional[LLamaMessageHistory] = None,
                 grammar: Optional[str] = None) -> str:
        """Uses LLM to generate a string

        Args:
            system_prompt (str): system prompt 
            user (str): user prompt
            temperature (Optional[float], optional): LLM temperature. Defaults to None.
            max_tokens (Optional[int], optional): LLM max tokens for generation. Defaults to None.
            grammar (Optional[str], optional): Llama.cpp grammar to constrain output. Defaults to None.

        Raises:
            last_exc

        Returns:
            str: generated string
        """
        headers = {"Content-Type": "application/json"}
        if payload is None:
            payload_dict = self._payload(system_prompt, user, temperature, max_tokens, grammar) # type: ignore
        else:
            payload_dict = {
                "model": self.model,
                "messages": payload.to_dict()
            }
            if temperature is not None:
                payload_dict["temperature"] = temperature
            if max_tokens is not None:
                payload_dict["max_tokens"] = max_tokens
            if grammar is not None:
                payload_dict["grammar"] = grammar
        
        last_exc = None
        for attempt in range(RETRIES + 1):
            try:
                print(payload_dict)
                r = httpx.post(self.url, json=payload_dict, timeout=TIMEOUT, headers=headers)
                r.raise_for_status()
                data = r.json()
                # обычный OAI-ответ
                msg = (data.get("choices") or [{}])[0].get("message", {})
                text = msg.get("content")
                # некоторые сборки кладут в choices[0].text
                if text is None:
                    text = (data.get("choices") or [{}])[0].get("text")
                with open("./storage/dev/response.txt", "a", encoding="utf-8") as f:
                    f.write("\n" + "-" * 10)
                    f.write(str(payload_dict))
                    f.write(str(text))
                    f.write("\n" + "-" * 10)
                return text or ""
            except Exception as e:
                last_exc = e
                time.sleep(min(2.0, 0.5 * attempt + 0.1))
        raise last_exc # type: ignore

        
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
                response_text = self.complete(
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
                response_text = self.complete(
                    system_prompt=system_prompt,
                    user=full_prompt,
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
        