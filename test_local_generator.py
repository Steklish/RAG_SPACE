# test_local_generator.py

import json
import os
import sys

# Add the 'app' directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from pydantic import BaseModel, Field
from app.local_generator import LocalGenerator

# Set the environment variable for the local server URL
os.environ["LLAMA_SERVER_URL"] = "http://127.0.0.1:8000/completion"

# 1. Define a simple Pydantic model
class Character(BaseModel):
    name: str = Field(description="The character's name")
    job: str = Field(description="The character's job")
    description: str = Field(description="A brief description of the character")

def run_test():
    print("--- Starting LocalGenerator Test ---")
    
    # 2. Instantiate the LocalGenerator
    try:
        generator = LocalGenerator()
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
                with open("generated_character.json", "w") as f:
                    json.dump(generated_character.model_dump(), f, indent=2)
                print("\nSuccessfully saved generated character to 'generated_character.json'")
            except Exception as e:
                print(f"\nError saving generated character to file: {e}")

        else:
            print("Generated object is not of the expected type 'Character'.")
            print(f"Received: {generated_character}")

    except Exception as e:
        print(f"\nAn error occurred during generation: {e}")

    print("\n--- Test Finished ---")

if __name__ == "__main__":
    run_test()
