import contextvars
from typing import Optional

# Context variables for logging
ctx_chat_id = contextvars.ContextVar("chat_id", default=None)
ctx_trace_id = contextvars.ContextVar("trace_id", default=None)

def set_chat_id(chat_id: Optional[int]):
    return ctx_chat_id.set(chat_id)

def get_chat_id() -> Optional[int]:
    return ctx_chat_id.get()

def set_trace_id(trace_id: str):
    return ctx_trace_id.set(trace_id)

def get_trace_id() -> Optional[str]:
    return ctx_trace_id.get()

def reset_chat_id(token):
    ctx_chat_id.reset(token)

def reset_trace_id(token):
    ctx_trace_id.reset(token)
