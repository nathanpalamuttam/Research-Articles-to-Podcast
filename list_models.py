from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found")
    exit(1)

client = genai.Client(api_key=api_key)

print("Listing all available models...\n")
print("="*80)

models = client.models.list()

for model in models:
    print(f"\nModel: {model.name}")
    if hasattr(model, 'display_name'):
        print(f"  Display Name: {model.display_name}")
    if hasattr(model, 'description'):
        print(f"  Description: {model.description}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")
    if hasattr(model, 'input_token_limit'):
        print(f"  Input Token Limit: {model.input_token_limit}")
    if hasattr(model, 'output_token_limit'):
        print(f"  Output Token Limit: {model.output_token_limit}")
    print("-"*80)
