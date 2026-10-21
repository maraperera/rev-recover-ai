import boto3
from langchain_aws import BedrockEmbeddings, ChatBedrock
from config.settings import settings


def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def get_bedrock_chat_llm() -> ChatBedrock:
    return ChatBedrock(
        client=get_bedrock_client(),
        model_id=settings.AWS_BEDROCK_MODEL_ID,
        model_kwargs={"temperature": 0.0, "max_tokens": 4096},
    )


def get_bedrock_embeddings() -> BedrockEmbeddings:
    return BedrockEmbeddings(
        client=get_bedrock_client(),
        model_id=settings.AWS_BEDROCK_EMBEDDING_ID,
    )