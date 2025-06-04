#!/usr/bin/env python3
"""
Test script to verify dual AI client functionality (Claude + OpenAI)
"""
import os
from dotenv import load_dotenv
from src.tinker.main import initialize_ai_client

def test_ai_client_initialization():
    """Test AI client initialization with different API key configurations."""
    load_dotenv()
    
    print("🧪 Testing AI Client Initialization")
    print("=" * 50)
    
    # Check what API keys are available
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print(f"ANTHROPIC_API_KEY: {'✅ Available' if anthropic_key else '❌ Not found'}")
    print(f"OPENAI_API_KEY: {'✅ Available' if openai_key else '❌ Not found'}")
    print()
    
    # Test client initialization
    client, client_type = initialize_ai_client()
    
    if client and client_type:
        print(f"✅ Successfully initialized {client_type.upper()} client")
        print(f"📝 Client type: {client_type}")
        print(f"🤖 Client object: {type(client).__name__}")
        
        if client_type == "anthropic":
            print("🎯 Using Claude Sonnet 4 (claude-3-5-sonnet-20241022)")
        elif client_type == "openai":
            print("🎯 Using OpenAI GPT-4")
            
    else:
        print("❌ No AI client could be initialized")
        print("💡 Make sure to set either ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file")
    
    print()
    print("🏁 Test completed!")

if __name__ == "__main__":
    test_ai_client_initialization()
