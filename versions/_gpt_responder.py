import os
from dotenv import load_dotenv
from openai import OpenAI

# Instantiate the client with your API key
load_dotenv()  # Load environment variables from .env
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

def generate_text(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0.7,
    )
    generated_text = response.choices[0].message.content.strip()
    return generated_text

# Example usage
prompt = "Explain the theory of relativity in one sentence"
result = generate_text(prompt)
print(result)