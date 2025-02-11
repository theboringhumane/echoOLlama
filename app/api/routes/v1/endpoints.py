from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_llm_service
from app.schemas.requests import (
    GenerateRequest,
    ChatRequest,
    PullRequest,
    GenerateResponse,
    ChatResponse,
    PullResponse
)
from app.services.llm import LLMService, ModelProvider
from app.utils.logger import logger

router = APIRouter()


@router.post("/generate")
async def generate_response(
        request: GenerateRequest,
        llm_service: LLMService = Depends(get_llm_service)
):
    """
    Generate a response using the specified model
    📝 File: endpoints.py, Line: 27, Function: generate_response
    """
    try:
        if request.stream:
            return StreamingResponse(
                llm_service.generate_response(
                    messages=request.messages,
                    temperature=request.temperature,
                    stream=True,
                    provider=ModelProvider.OLLAMA if "llama" in request.model.lower() else ModelProvider.OPENAI
                ),
                media_type="text/event-stream"
            )

        response = await llm_service.generate_response(
            messages=request.messages,
            temperature=request.temperature,
            stream=False,
            provider=ModelProvider.OLLAMA if "llama" in request.model.lower() else ModelProvider.OPENAI
        )
        return GenerateResponse(
            model=request.model,
            response=response.choices[0].message.content,
            done=True
        )

    except Exception as e:
        logger.error(f"❌ endpoints.py: Generate response failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_with_model(
        request: ChatRequest,
        llm_service: LLMService = Depends(get_llm_service)
):
    """
    Have a conversation with the model
    📝 File: endpoints.py, Line: 64, Function: chat_with_model
    """
    try:
        if request.stream:
            return StreamingResponse(
                llm_service.chat_stream(
                    request=request,
                    provider=ModelProvider.OLLAMA if "llama" in request.model.lower() else ModelProvider.OPENAI
                ),
                media_type="text/event-stream"
            )

        response = await llm_service.generate_response(
            messages=[m.model_dump() for m in request.messages],
            temperature=0.8,
            stream=False,
            provider=ModelProvider.OLLAMA if "llama" in request.model.lower() else ModelProvider.OPENAI
        )

        return ChatResponse(
            model=request.model,
            message={
                "role": "assistant",
                "content": response.choices[0].message.content
            },
            done=True
        )

    except Exception as e:
        logger.error(f"❌ endpoints.py: Chat with model failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=Dict)
async def list_models(
        llm_service: LLMService = Depends(get_llm_service)
):
    """
    List all available models
    📝 File: endpoints.py, Line: 105, Function: list_models
    """
    try:
        # Get models from both providers
        ollama_models = await llm_service.ollama_client.list()
        return ollama_models

    except Exception as e:
        logger.error(f"❌ endpoints.py: List models failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/model/pull", response_model=PullResponse)
async def pull_model(
        request: PullRequest,
        llm_service: LLMService = Depends(get_llm_service)
):
    """
    Pull a model from the provider
    📝 File: endpoints.py, Line: 144, Function: pull_model
    """
    try:
        if "ollama" in request.provider.lower():
            # Only Ollama supports model pulling
            await llm_service.ollama_client.pull(request.name)
            return PullResponse(status="success", model=request.name)
        else:
            raise HTTPException(status_code=400, detail="Model pulling only supported for Ollama models")

    except Exception as e:
        logger.error(f"❌ endpoints.py: Pull model failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/model/{model_name}")
async def delete_model(
        model_name: str,
        provider: str = "ollama",
        llm_service: LLMService = Depends(get_llm_service)
):
    """
    Delete a model
    📝 File: endpoints.py, Line: 166, Function: delete_model
    """
    try:
        if "ollama" in provider.lower():
            # Only Ollama supports model deletion
            await llm_service.ollama_client.delete(model_name)
            return {"status": "success", "message": f"Model {model_name} deleted"}
        else:
            raise HTTPException(status_code=400, detail="Model deletion only supported for Ollama models")

    except Exception as e:
        logger.error(f"❌ endpoints.py: Delete model failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
