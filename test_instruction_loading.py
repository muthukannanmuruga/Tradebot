"""
Test if deepseek_instruction.md is being loaded correctly
"""
from app.deepseek_ai import DeepSeekAI
from app.config import config

print("="*70)
print("Testing DeepSeek Instruction File Loading")
print("="*70)

print(f"\n📁 Instruction Path from Config: '{config.DEEPSEEK_INSTRUCTION_PATH}'")

ai = DeepSeekAI()

print(f"\n📄 Instruction Text Loaded: {ai.instruction_text is not None}")

if ai.instruction_text:
    print(f"✅ Using instruction file: deepseek_instruction.md")
    print(f"📝 First 200 characters:")
    print(f"   {ai.instruction_text[:200]}...")
    print(f"\n🔍 Checking for multi-timeframe keywords:")
    keywords = ["multi-timeframe", "5-minute", "1-hour", "4-hour", "1-day", "timeframe alignment"]
    for keyword in keywords:
        found = keyword.lower() in ai.instruction_text.lower()
        status = "✅" if found else "❌"
        print(f"   {status} '{keyword}': {found}")
else:
    print(f"⚠️ No instruction file loaded, using fallback system prompt")
    fallback = ai._get_system_prompt()
    print(f"📝 Fallback prompt first 200 characters:")
    print(f"   {fallback[:200]}...")

print("\n" + "="*70)
print("CONFIGURATION INSTRUCTIONS")
print("="*70)
print("""
To use the multi-timeframe instruction file:

1. Create a .env file (copy from .env.example):
   cp .env.example .env

2. Set your API keys in .env

3. Ensure this line is in your .env:
   DEEPSEEK_INSTRUCTION_PATH=deepseek_instruction.md

4. The file deepseek_instruction.md should be in the root directory

5. Restart the bot to load the new instructions
""")
print("="*70)
