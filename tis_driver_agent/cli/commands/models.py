"""Models command - list available models and their requirements."""


def cmd_models(args):
    """List available models and their requirements."""
    print("""
AVAILABLE MODELS
================

Models are auto-detected by name prefix. Use any model name with --model.

ANTHROPIC (Claude) - requires ANTHROPIC_API_KEY
------------------------------------------------
  Claude 4.5 (Latest):
    claude-sonnet-4-5             Smart, complex agents/coding     $3/$15 per MTok
    claude-haiku-4-5              Fastest, near-frontier           $1/$5 per MTok
    claude-opus-4-5               Max intelligence                 $5/$25 per MTok

  Claude 4:
    claude-sonnet-4-20250514
    claude-opus-4-20250514

  Claude 3.5:
    claude-3-5-sonnet-20241022
    claude-3-5-haiku-20241022

OPENAI - requires OPENAI_API_KEY
--------------------------------
  Recommended:
    gpt-4o-mini                   Fast, cheap, good quality        $0.15/$0.60 per MTok
    gpt-4o                        More capable                     $2.50/$10 per MTok

  Others: gpt-4-turbo, gpt-4.1-mini, gpt-4.1-nano, o1-mini, o3-mini, etc.

OLLAMA (Local) - free, requires Ollama running
----------------------------------------------
  llama3.2:latest                 Good general purpose
  codellama:latest                Code-focused
  mistral:7b-instruct             Fast and capable
  deepseek-coder:latest           Code-focused

  Any model starting with: llama, mistral, gemma, codellama, deepseek,
  qwen, phi, vicuna, orca, neural-chat, starling, dolphin

ENVIRONMENT SETUP
-----------------
  Anthropic: export ANTHROPIC_API_KEY='sk-ant-...'
  OpenAI:    export OPENAI_API_KEY='sk-...'
  Ollama:    ollama serve  (then: ollama pull <model>)

  Or add keys to .env file in current directory.
""")
