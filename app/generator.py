# generator.py

import os
import json
import time
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import google.generativeai as genai

from colors import *

# A Generic Type Variable for our generator's return type
T = TypeVar("T", bound=BaseModel)


class ObjectGenerator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing the Gemini API to return a JSON object.
    """

    def __init__(self):
        """
        Initializes the generator with Google API credentials.
        """
        genai.configure(api_key=os.getenv("GEMINI_API_KEY")) # pyright: ignore[reportPrivateImportUsage]
        self.model = genai.GenerativeModel( # pyright: ignore[reportPrivateImportUsage]
            os.getenv("GEMINI_MODEL") # pyright: ignore[reportArgumentType]
        )

    def _clean_json_response(self, text_response: str) -> str:
        """
        Cleans the raw text response from the model to isolate the JSON object.
        """
        start_index = text_response.find("{")
        if start_index == -1:
            raise ValueError("No JSON object found in the response.")

        end_index = text_response.rfind("}")
        if end_index == -1:
            raise ValueError("No JSON object found in the response.")

        return text_response[start_index : end_index + 1]

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
            context: Optional context to guide the generation.
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

        for i in range(retries):
            print(
                f"{HEADER_COLOR}Sending request to Gemini{Colors.RESET} for: {ENTITY_COLOR}{pydantic_model.__name__}{Colors.RESET} (Language: {INFO_COLOR}{language or 'Default'}{Colors.RESET})"
            )
            try:
                response = self.model.generate_content(full_prompt)
                cleaned_response = self._clean_json_response(response.text)
                parsed_data = json.loads(cleaned_response)
                return pydantic_model(**parsed_data)
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                print(
                    f"{ERROR_COLOR}Error processing Gemini response (attempt {i + 1}/{retries}):{Colors.RESET} {e}"
                )
                print(f"{WARNING_COLOR}Raw Response from API:{Colors.RESET}")
                print(response.text) # type: ignore
                print(f"{Colors.DIM}{'─' * 30}{Colors.RESET}")
                if i < retries - 1:
                    print(f"{INFO_COLOR}Retrying in {delay} seconds...{Colors.RESET}")
                    time.sleep(delay)
                else:
                    raise e
        raise Exception("Failed to generate object after multiple retries.")
