import os
import time
import random
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

def create_tinker_folder():
    """Create .tinker folder in current directory if it doesn't exist."""
    tinker_folder = Path.cwd() / ".tinker"
    tinker_folder.mkdir(exist_ok=True)
    print(f"Created/verified .tinker folder at: {tinker_folder}")
    return tinker_folder

def generate_gibberish():
    """Generate random gibberish text."""
    words = ["beep", "boop", "whirr", "click", "buzz", "hum", "zap", "ping", "tick", "whiz"]
    symbols = ["!", "@", "#", "$", "%", "^", "&", "*", "~", "+"]
    
    gibberish = []
    for _ in range(random.randint(3, 8)):
        if random.choice([True, False]):
            gibberish.append(random.choice(words))
        else:
            gibberish.append(random.choice(symbols))
    
    return " ".join(gibberish)

def main():
    """Main Tinker CLI that runs forever."""
    # Load environment variables from .env file
    load_dotenv()
    
    print("🔧 Tinker - Autonomous AI Agent Starting...")
    print("Building and maintaining Pixel...")
    
    # Create .tinker folder
    tinker_folder = create_tinker_folder()
    
    # Initialize OpenAI client (though we're not using it for gibberish yet)
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("✅ OpenAI client initialized")
    except Exception as e:
        print(f"⚠️  OpenAI client initialization failed: {e}")
        print("Continuing with gibberish generation...")
    
    print("\n🚀 Tinker is now running...")
    print("Generating activity every 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Generate and display gibberish
            gibberish = generate_gibberish()
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Tinker: {gibberish}")
            
            # Wait 5 seconds
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Tinker stopped by user")
        print("Goodbye!")

if __name__ == "__main__":
    main()