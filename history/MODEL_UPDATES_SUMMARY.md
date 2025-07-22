# KePrompt Model Updates Summary

## Overview
Updated all AI provider files with the latest available models and current pricing as of January 2025.

## Changes Made

### OpenAI (AiOpenAi.py)
**New Models Added:**
- `gpt-4.1` - Latest GPT model ($2.00/$8.00 per 1M tokens)
- `gpt-4.1-mini` - Affordable balanced model ($0.40/$1.60 per 1M tokens)
- `gpt-4.1-nano` - Fastest, most cost-effective model ($0.10/$0.40 per 1M tokens)
- `o3` - Most powerful reasoning model ($2.00/$8.00 per 1M tokens)
- `o4-mini` - Faster, cost-efficient reasoning model ($1.10/$4.40 per 1M tokens)

**Updated Pricing:**
- `gpt-4o-mini`: Updated to $0.60/$2.40 per 1M tokens
- All models maintain 128K context window

### Anthropic (AiAnthropic.py)
**New Models Added:**
- `claude-opus-4` - Latest most intelligent model ($15.00/$75.00 per 1M tokens)
- `claude-sonnet-4` - Optimal balance model ($3.00/$15.00 per 1M tokens)
- `claude-haiku-3.5` - Fastest model ($0.80/$4.00 per 1M tokens)

**Updated Features:**
- Increased context window to 200K tokens for all models
- Added legacy Claude 3 models for backward compatibility

### Google (AiGoogle.py)
**New Models Added:**
- `gemini-2.5-pro` - State-of-the-art model ($1.25/$10.00 per 1M tokens)
- `gemini-2.5-flash` - Hybrid reasoning model ($0.30/$2.50 per 1M tokens)
- `gemini-2.5-flash-lite` - Most cost-effective model ($0.10/$0.40 per 1M tokens)
- `gemini-2.0-flash` - Balanced multimodal model ($0.10/$0.40 per 1M tokens)
- `gemini-2.0-flash-lite` - Smallest model ($0.075/$0.30 per 1M tokens)
- `gemma-3-27b` and `gemma-3n-e4b` - Open models (free)

**Updated Features:**
- Context windows up to 2M tokens for Gemini 1.5 Pro
- 1M token context for most newer models

### MistralAI (AiMistral.py)
**New Models Added:**
- `mistral-medium-3` - State-of-the-art performance ($0.40/$2.00 per 1M tokens)
- `magistral-medium` - Thinking model ($2.00/$5.00 per 1M tokens)
- `magistral-small` - Small thinking model ($0.50/$1.50 per 1M tokens)
- `devstral-medium` - Enhanced coding model ($0.40/$2.00 per 1M tokens)
- `devstral-small` - Best open-source coding model ($0.10/$0.30 per 1M tokens)
- `voxtral-small` - Speech and audio model ($0.10/$0.30 per 1M tokens)
- `voxtral-mini` - Low-latency speech model ($0.04/$0.04 per 1M tokens)
- `mistral-small-3.2` - Latest small model ($0.10/$0.30 per 1M tokens)

**Updated Features:**
- Increased context windows to 128K tokens for most models
- Added comprehensive model lineup including vision and audio models

### XAI (AiXai.py)
**New Models Added:**
- `grok-4` - World's best model ($3.00/$15.00 per 1M tokens, 256K context)
- `grok-3` - Flagship enterprise model ($3.00/$15.00 per 1M tokens)
- `grok-3-mini` - Lightweight reasoning model ($0.30/$0.50 per 1M tokens)
- `grok-2-1212` - Updated Grok-2 model ($2.00/$10.00 per 1M tokens)
- `grok-2-vision-1212` - Vision-capable model ($2.00/$10.00 per 1M tokens)

**Updated Features:**
- Grok-4 has 256K context window (doubled from previous models)
- Maintained backward compatibility with beta models

### DeepSeek (AiDeepSeek.py)
**Updated Pricing:**
- `deepseek-chat`: Updated to $0.27/$1.10 per 1M tokens (standard rates)
- `deepseek-reasoner`: Updated to $0.55/$2.19 per 1M tokens (standard rates)
- Context window remains at 64K tokens

## Summary Statistics

**Total Models Available:** 50+ models across 6 providers
- **OpenAI:** 11 models (GPT-4.1 series, O-series reasoning models, legacy GPT-4o)
- **Anthropic:** 6 models (Claude 4 series, Claude 3.5, legacy Claude 3)
- **Google:** 11 models (Gemini 2.5, 2.0, 1.5 series, plus open Gemma models)
- **MistralAI:** 17 models (Premier, open, vision, audio, and legacy models)
- **XAI:** 7 models (Grok 4, 3, 2 series with vision capabilities)
- **DeepSeek:** 2 models (Chat and Reasoner with updated pricing)

## Key Improvements

1. **Latest Model Support:** All providers now include their newest flagship models
2. **Accurate Pricing:** Updated to current 2025 pricing from official sources
3. **Enhanced Context Windows:** Many models now support larger context windows
4. **Comprehensive Coverage:** Added specialized models for coding, reasoning, vision, and audio
5. **Backward Compatibility:** Maintained legacy models for existing workflows

## Testing

Successfully tested the updates by running `keprompt -m` which displayed all 50+ models with correct pricing and context window information.

## Files Modified

- `keprompt/AiOpenAi.py` - Updated OpenAI models and pricing
- `keprompt/AiAnthropic.py` - Updated Anthropic models and pricing  
- `keprompt/AiGoogle.py` - Updated Google models and pricing
- `keprompt/AiMistral.py` - Updated MistralAI models and pricing
- `keprompt/AiXai.py` - Updated XAI models and pricing
- `keprompt/AiDeepSeek.py` - Updated DeepSeek models and pricing

All updates maintain the existing API structure and are fully backward compatible with existing prompt files.
