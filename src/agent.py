"""
Reply Agent Core Implementation
"""
from pydantic import BaseModel, Field
from configs.settings import settings, BrandConfig
from src.llm import LLMClient


class CustomerInquiry(BaseModel):
    customer_id: str
    message: str
    channel: str = "email"


class ReplyResponse(BaseModel):
    customer_id: str
    reply_text: str
    brand_name: str
    status: str = "success"


class ReplyAgent:
    def __init__(self, brand_config: BrandConfig = settings.brand):
        self.brand_config = brand_config
        self.llm_client = LLMClient()

    def process_inquiry(self, inquiry: CustomerInquiry) -> ReplyResponse:
        reply_text = self.llm_client.generate_reply(inquiry.message)
        return ReplyResponse(
            customer_id=inquiry.customer_id,
            reply_text=reply_text,
            brand_name=self.brand_config.brand_name
        )
