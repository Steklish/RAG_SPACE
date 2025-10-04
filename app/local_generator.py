# local_generator.py

import os
import json
import time
from typing import Type, TypeVar, Optional
import httpx
from pydantic import BaseModel, Field, ValidationError
import requests

from colors import *

# A Generic Type Variable for our generator's return type
T = TypeVar("T", bound=BaseModel)

RETRIES = int(os.getenv("LLAMA_API_RETRIES", 3))
TIMEOUT = int(os.getenv("LLAMA_API_TIMEOUT", 30))

class LocalGenerator:
    """
    A class to generate instances of Pydantic models in a specified language
    by instructing a local Llama server to return a JSON object.
    """

    def __init__(self, model : str, base: str):
        """
        Initializes the generator with the local Llama server URL.
        """
        self.model = model
        self.base = base
        self.url = f"{self.base}/v1/chat/completions"
    
    def _payload(self, system_prompt: str, user: str, temperature: Optional[float], max_tokens: Optional[int]):
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
        return body

        
    def complete(self, system_prompt: str, user: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        url = f"{self.base}/v1/chat/completions"
        payload = self._payload(system_prompt, user, temperature, max_tokens)

        last_exc = None
        for attempt in range(RETRIES + 1):
            try:
                r = httpx.post(url, json=payload, timeout=TIMEOUT)
                r.raise_for_status()
                data = r.json()
                # обычный OAI-ответ
                msg = (data.get("choices") or [{}])[0].get("message", {})
                text = msg.get("content")
                # некоторые сборки кладут в choices[0].text
                if text is None:
                    text = (data.get("choices") or [{}])[0].get("text")
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

    def generate(
        self,
        pydantic_model: Type[T],
        prompt: Optional[str] = None,
        language: Optional[str] = None,
        retries: int = RETRIES,
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
                print(f"{INFO_COLOR} url {self.url}:{Colors.RESET}")
                # response = requests.post(self.url, headers=headers, json=data)
                response_text = self.complete(system_prompt="",
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

if __name__ == "__main__": 
    
    # 1. Define a simple Pydantic model
    class Character(BaseModel):
        name: str = Field(description="The character's name")
        job: str = Field(description="The character's job")
        description: str = Field(description="A brief description of the character")

    def run_test():
        print("--- Starting LocalGenerator Test ---")
        
        # 2. Instantiate the LocalGenerator
        try:
            generator = LocalGenerator(
                            model="gemma-3n-E4B-it-Q4_0.gguf",
                            base = os.getenv("LLAMA_SERVER_URL", "http://localhost:8080")) 
            
            
            print("LocalGenerator instantiated successfully.")
        except Exception as e:
            print(f"Error instantiating LocalGenerator: {e}")
            return

        # 3. Define a prompt
        prompt = "Create a fantasy character who is a clumsy wizard."
        print(f"Test prompt: '{prompt}'")

        # 4. Call the generate method
        try:
            print("Generating object...")
            generated_character = generator.generate(
                pydantic_model=Character,
                prompt=prompt,
                language="English"
            )
            
            # 5. Print the result
            print("\n--- Test Result ---")
            if isinstance(generated_character, Character):
                print("Successfully generated a Character object:")
                print(f"  Name: {generated_character.name}")
                print(f"  Job: {generated_character.job}")
                print(f"  Description: {generated_character.description}")

                # Save the generated object to a JSON file
                try:
                    with open("generated_character.json", "w", encoding="utf-8") as f:
                        json.dump(generated_character.model_dump(), f, indent=2)
                    print("\nSuccessfully saved generated character to 'generated_character.json'")
                    
                    # Save the generated object to a text file
                    with open("llm_response.txt", "w", encoding="utf-8") as f:
                        f.write(str(generated_character))
                    print("Successfully saved LLM response to 'llm_response.txt'")
                except Exception as e:
                    print(f"\nError saving generated character to file: {e}")

            else:
                print("Generated object is not of the expected type 'Character'.")
                # print(f"Received: {generated_character}")
                
                # Save the raw response to a text file
                try:
                    with open("llm_response.txt", "w", encoding="utf-8") as f:
                        f.write(str(generated_character))
                    print("\nSuccessfully saved raw LLM response to 'llm_response.txt'")
                except Exception as e:
                    print(f"\nError saving raw LLM response to file: {e}")

        except Exception as e:
            print(f"\nAn error occurred during generation: {str(e).encode('utf-8')}")

        print("\n--- Test Finished ---")
        
    run_test()