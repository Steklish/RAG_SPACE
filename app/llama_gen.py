# llama_gen.py

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


class LlamaGenAI:
    """
    A class to interact with a local Llama server for generating text and Pydantic models
    """

    def __init__(self, base: str):
        """
        Initializes the generator with the local Llama server URL.
        """
        self.base = base
        self.model = self._get_model_from_server()
        self.url = f"{self.base}/v1/chat/completions"
        print(f"{SUCCESS_COLOR}LlamaGenAI instantiated successfully.{Colors.RESET}")

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