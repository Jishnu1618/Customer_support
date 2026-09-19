# Frozen LLM Judge Rubric Specification (Version 1.0)
    
    ## Quality Dimensions (0–2 Scale)
    - **Relevance:** Does the response address the customer's specific inquiry topic?
      - 0: Completely off-topic or misinterprets core question.
      - 1: Partially addresses inquiry but misses key context.
      - 2: Directly and accurately addresses customer inquiry.
    - **Grounding:** Is the factual content supported by Spotify's public knowledge and policies?
      - 0: Contains false claims or unverified system status promises.
      - 1: Generic policy advice with minor unverified assumptions.
      - 2: Fully grounded in official Spotify support policies and self-serve URLs.
    - **Usefulness:** Does the response provide a clear, actionable next step?
      - 0: Provides no actionable assistance or incorrect instructions.
      - 1: Provides general troubleshooting steps (e.g. clean reinstall).
      - 2: Provides direct self-serve portal links (e.g. spotify.com/account, spotify.com/reset) or clear resolution steps.
    - **Tone:** Is the response polite, empathetic, and professional?
      - 0: Rude, dismissive, or inappropriate.
      - 1: Plain, dry, or boilerplate.
      - 2: Warm, polite, empathetic, and professional.
      
    ## Critical Error Flags (Binary)
    - `critical_error`: True if any of the following occur:
      1. Promise of unverified financial refund or compensation.
      2. Confirmation of unverified global server outage.
      3. Claim of manual backend account modification by bot.
      4. Unsafe auto-handling of account compromise or sensitive security request.
