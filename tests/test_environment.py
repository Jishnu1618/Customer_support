"""
Environment and Setup Tests
"""
from configs.settings import settings, BrandConfig
from src.agent import ReplyAgent, CustomerInquiry


def test_package_imports():
    """Verify all required libraries are installed and importable."""
    import pandas as pd
    import sklearn
    import pydantic
    import google.genai
    import openai
    import anthropic

    assert pd.__version__ is not None
    assert sklearn.__version__ is not None
    assert pydantic.__version__ is not None
    assert google.genai is not None
    assert openai is not None
    assert anthropic is not None


def test_brand_config():
    """Verify brand configuration loads default values."""
    config = settings.brand
    assert isinstance(config, BrandConfig)
    assert config.brand_name == "SpotifyCares"
    assert len(config.guidelines) > 0


def test_reply_agent_instantiation():
    """Verify ReplyAgent processes sample inquiry."""
    agent = ReplyAgent()
    inquiry = CustomerInquiry(customer_id="CUST-001", message="How do I reset my password?")
    response = agent.process_inquiry(inquiry)
    
    assert response.customer_id == "CUST-001"
    assert response.brand_name == "SpotifyCares"
    assert response.status == "success"
    assert len(response.reply_text) > 0

