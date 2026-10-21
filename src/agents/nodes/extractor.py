from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentAuditState, InvoicePayload
from src.utils.bedrock_client import get_bedrock_chat_llm

EXTRACTION_PROMPT = """You are an expert accounts payable AI agent. 
Extract all invoice details from the text below into the strict schema.
Text:
{raw_text}
"""


async def extract_invoice_node(state: AgentAuditState) -> dict:
    llm = get_bedrock_chat_llm()
    structured_llm = llm.with_structured_output(InvoicePayload)

    prompt = ChatPromptTemplate.from_template(EXTRACTION_PROMPT)
    chain = prompt | structured_llm

    result: InvoicePayload = await chain.ainvoke({"raw_text": state["raw_document_text"]})
    return {"extracted_invoice": result}