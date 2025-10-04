# local_generator.py

import os
import json
import time
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import requests

from colors import *

# A Generic Type Variable for our generator's return type
T = TypeVar("T", bound=BaseModel)


class LocalGenerator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing a local Llama server to return a JSON object.
    """

    def __init__(self):
        """
        Initializes the generator with the local Llama server URL.
        """
        self.server_url = os.getenv("LLAMA_SERVER_URL", "http://localhost:8080/completion")

    def _clean_json_response(self, response_data: dict) -> str:
        """
        Cleans the raw text response from the model to isolate the JSON object.
        """
        # Check for JSON in the 'content' field first
        text_response = response_data.get("content", "")
        start_index = text_response.find("{")
        if start_index != -1:
            end_index = text_response.rfind("}")
            if end_index != -1:
                return text_response[start_index : end_index + 1]

        # If not in 'content', check the 'prompt' field
        text_response = response_data.get("prompt", "")
        # Find the last occurrence of a JSON object
        last_brace_open = text_response.rfind("{")
        if last_brace_open != -1:
            # Find the corresponding closing brace
            last_brace_close = text_response.rfind("}")
            if last_brace_close > last_brace_open:
                return text_response[last_brace_open : last_brace_close + 1]

        raise ValueError("No JSON object found in the response.")

    def generate(
        self,
        pydantic_model: Type[T],
        prompt: Optional[str] = None,
        language: Optional[str] = None,
        retries: int = 3,
        delay: int = 5,
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


        # --- NEW: Language Instruction ---
        language_instruction = ""
        if language:
            language_instruction = f"CRITICAL: All generated text content (like names, descriptions, effects, etc.) MUST be in the following language: {language}."

        # --- Construct the full prompt with the new language instruction ---
        full_prompt = f"""
        You are a data generation assistant. Your task is to create a JSON object that strictly adheres to the provided JSON schema.

        JSON Schema:
        ```json
        {schema_json}
        ```

        Request:
        {user_request}
        {language_instruction}

        IMPORTANT: Your response MUST be ONLY the valid JSON object that conforms to the schema. Do not include any other text, explanations, or markdown formatting like ```json.
        """

        headers = {"Content-Type": "application/json"}
        data = {
            "prompt": full_prompt,
            "n_predict": 2048, # Max tokens to generate
            "temperature": 0.7,
            "stop": ["\n"]
        }

        for i in range(retries):
            print(
                f"{HEADER_COLOR}Sending request to Local Llama Server{Colors.RESET} for: {ENTITY_COLOR}{pydantic_model.__name__}{Colors.RESET} (Language: {INFO_COLOR}{language or 'Default'}{Colors.RESET})"
            )
            try:
                response = requests.post(self.server_url, headers=headers, json=data)
                response.raise_for_status()
                
                response_json = response.json()
                cleaned_response = self._clean_json_response(response_json)
                try:
                    parsed_data = json.loads(cleaned_response)
                except json.JSONDecodeError as e:
                    print(f"{ERROR_COLOR}Error decoding JSON: {e}{Colors.RESET}")
                    print(f"{WARNING_COLOR}Cleaned Response that failed parsing:{Colors.RESET}")
                    print(cleaned_response)
                    raise e
                return pydantic_model(**parsed_data)
            except (requests.exceptions.RequestException, json.JSONDecodeError, ValidationError, ValueError) as e:
                print(
                    f"{ERROR_COLOR}Error processing response (attempt {i + 1}/{retries}):{Colors.RESET} {e}"
                )
                if 'response' in locals() and response.text:
                    print(f"{WARNING_COLOR}Raw Response from API:{Colors.RESET}")
                    print(response.text)
                print(f"{Colors.DIM}{'─' * 30}{Colors.RESET}")
                if i < retries - 1:
                    print(f"{INFO_COLOR}Retrying in {delay} seconds...{Colors.RESET}")
                    time.sleep(delay)
                else:
                    raise e
        raise Exception("Failed to generate object after multiple retries.")
