# Manage memory
[](https://github.com/langchain-ai/langgraph/edit/main/docs/docs/how-tos/memory.ipynb "Edit this page")

Many AI applications need memory to share context across multiple interactions. LangGraph supports two types of memory essential for building conversational agents:

*   [Short-term memory](#add-short-term-memory): Tracks the ongoing conversation by maintaining message history within a session.
*   [Long-term memory](#add-long-term-memory): Stores user-specific or application-level data across sessions.

With [short-term memory](#add-short-term-memory) enabled, long conversations can exceed the LLM's context window. Common solutions are:

*   [Trimming](#trim-messages): Remove first or last N messages (before calling LLM)
*   [Summarization](#summarize-messages): Summarize earlier messages in the history and replace them with a summary
*   [Delete messages](#delete-messages) from LangGraph state permanently
*   custom strategies (e.g., message filtering, etc.)

This allows the agent to keep track of the conversation without exceeding the LLM's context window.

Add short-term memory
-----------------------------------------------------------------

Short-term memory enables agents to track multi-turn conversations:

_API Reference: [InMemorySaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.memory.InMemorySaver) | [StateGraph](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.state.StateGraph)_

```
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph

checkpointer = InMemorySaver()

builder = StateGraph(...)
graph = builder.compile(checkpointer=checkpointer)

graph.invoke(
    {"messages": [{"role": "user", "content": "hi! i am Bob"}]},
    {"configurable": {"thread_id": "1"}},
)

```


See the [persistence](about:blank/persistence#add-short-term-memory) guide to learn more about working with short-term memory.

Add long-term memory
---------------------------------------------------------------

Use long-term memory to store user-specific or application-specific data across conversations. This is useful for applications like chatbots, where you want to remember user preferences or other information.

_API Reference: [StateGraph](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.state.StateGraph)_

```
from langgraph.store.memory import InMemoryStore
from langgraph.graph import StateGraph

store = InMemoryStore()

builder = StateGraph(...)
graph = builder.compile(store=store)

```


See the [persistence](about:blank/persistence#add-long-term-memory) guide to learn more about working with long-term memory.

Trim messages
-------------------------------------------------

To trim message history, you can use [`trim_messages`](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.utils.trim_messages.html) function:

_API Reference: [trim\_messages](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.utils.trim_messages.html) | [count\_tokens\_approximately](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.utils.count_tokens_approximately.html)_

```
from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)

def call_model(state: MessagesState):
    messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=128,
        start_on="human",
        end_on=("human", "tool"),
    )
    response = model.invoke(messages)
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node(call_model)
...

```


Full example: trim messages

```
from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, MessagesState

model = init_chat_model("anthropic:claude-3-7-sonnet-latest")
summarization_model = model.bind(max_tokens=128)

def call_model(state: MessagesState):
    messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=128,
        start_on="human",
        end_on=("human", "tool"),
    )
    response = model.invoke(messages)
    return {"messages": [response]}

checkpointer = InMemorySaver()
builder = StateGraph(MessagesState)
builder.add_node(call_model)
builder.add_edge(START, "call_model")
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}
graph.invoke({"messages": "hi, my name is bob"}, config)
graph.invoke({"messages": "write a short poem about cats"}, config)
graph.invoke({"messages": "now do the same but for dogs"}, config)
final_response = graph.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()

```


```
================================== Ai Message ==================================

Your name is Bob, as you mentioned when you first introduced yourself.

```


Summarize messages
-----------------------------------------------------------

An effective strategy for handling long conversation history is to summarize earlier messages once they reach a certain threshold:

_API Reference: [AnyMessage](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.AnyMessage.html) | [count\_tokens\_approximately](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.utils.count_tokens_approximately.html) | [StateGraph](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.state.StateGraph) | [START](https://langchain-ai.github.io/langgraph/reference/constants/#langgraph.constants.START)_

```
from typing import Any, TypedDict

from langchain_core.messages import AnyMessage
from langchain_core.messages.utils import count_tokens_approximately
from langmem.short_term import SummarizationNode
from langgraph.graph import StateGraph, START, MessagesState

class State(MessagesState):
    context: dict[str, Any]  # (1)!

class LLMInputState(TypedDict):  # (2)!
    summarized_messages: list[AnyMessage]
    context: dict[str, Any]

summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,
    model=summarization_model,
    max_tokens=512,
    max_tokens_before_summary=256,
    max_summary_tokens=256,
)

def call_model(state: LLMInputState):  # (3)!
    response = model.invoke(state["summarized_messages"])
    return {"messages": [response]}

builder = StateGraph(State)
builder.add_node(call_model)
builder.add_node("summarize", summarization_node)
builder.add_edge(START, "summarize")
builder.add_edge("summarize", "call_model")
...

```


1.  We will keep track of our running summary in the `context` field (expected by the `SummarizationNode`).
2.  Define private state that will be used only for filtering the inputs to `call_model` node.
3.  We're passing a private input state here to isolate the messages returned by the summarization node

Full example: summarize messages

```
from typing import Any, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langmem.short_term import SummarizationNode

model = init_chat_model("anthropic:claude-3-7-sonnet-latest")
summarization_model = model.bind(max_tokens=128)

class State(MessagesState):
    context: dict[str, Any]  # (1)!

class LLMInputState(TypedDict):  # (2)!
    summarized_messages: list[AnyMessage]
    context: dict[str, Any]

summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,
    model=summarization_model,
    max_tokens=256,
    max_tokens_before_summary=256,
    max_summary_tokens=128,
)

def call_model(state: LLMInputState):  # (3)!
    response = model.invoke(state["summarized_messages"])
    return {"messages": [response]}

checkpointer = InMemorySaver()
builder = StateGraph(State)
builder.add_node(call_model)
builder.add_node("summarize", summarization_node)
builder.add_edge(START, "summarize")
builder.add_edge("summarize", "call_model")
graph = builder.compile(checkpointer=checkpointer)

# Invoke the graph
config = {"configurable": {"thread_id": "1"}}
graph.invoke({"messages": "hi, my name is bob"}, config)
graph.invoke({"messages": "write a short poem about cats"}, config)
graph.invoke({"messages": "now do the same but for dogs"}, config)
final_response = graph.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
print("\nSummary:", final_response["context"]["running_summary"].summary)

```


1.  We will keep track of our running summary in the `context` field (expected by the `SummarizationNode`).
2.  Define private state that will be used only for filtering the inputs to `call_model` node.
3.  We're passing a private input state here to isolate the messages returned by the summarization node

```
================================== Ai Message ==================================

From our conversation, I can see that you introduced yourself as Bob. That's the name you shared with me when we began talking.

Summary: In this conversation, I was introduced to Bob, who then asked me to write a poem about cats. I composed a poem titled "The Mystery of Cats" that captured cats' graceful movements, independent nature, and their special relationship with humans. Bob then requested a similar poem about dogs, so I wrote "The Joy of Dogs," which highlighted dogs' loyalty, enthusiasm, and loving companionship. Both poems were written in a similar style but emphasized the distinct characteristics that make each pet special.

```


Delete messages
-----------------------------------------------------

To delete messages from the graph state, you can use the `RemoveMessage`.

*   Remove specific messages:
    
    ```
from langchain_core.messages import RemoveMessage

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # remove the earliest two messages
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}

```

    
*   Remove **all** messages:
    
    ```
from langgraph.graph.message import REMOVE_ALL_MESSAGES

def delete_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}

```

    

Valid message history

When deleting messages, **make sure** that the resulting message history is valid. Check the limitations of the LLM provider you're using. For example:

*   some providers expect message history to start with a `user` message
*   most providers require `assistant` messages with tool calls to be followed by corresponding `tool` result messages.

Full example: delete messages

```
from langchain_core.messages import RemoveMessage

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # remove the earliest two messages
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}

builder = StateGraph(MessagesState)
builder.add_sequence([call_model, delete_messages])
builder.add_edge(START, "call_model")

checkpointer = InMemorySaver()
app = builder.compile(checkpointer=checkpointer)

for event in app.stream(
    {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
    config,
    stream_mode="values"
):
    print([(message.type, message.content) for message in event["messages"]])

for event in app.stream(
    {"messages": [{"role": "user", "content": "what's my name?"}]},
    config,
    stream_mode="values"
):
    print([(message.type, message.content) for message in event["messages"]])

```


```
[('human', "hi! I'm bob")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! How are you doing today? Is there anything I can help you with?')]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! How are you doing today? Is there anything I can help you with?'), ('human', "what's my name?")]
[('human', "hi! I'm bob"), ('ai', 'Hi Bob! How are you doing today? Is there anything I can help you with?'), ('human', "what's my name?"), ('ai', 'Your name is Bob.')]
[('human', "what's my name?"), ('ai', 'Your name is Bob.')]

```
