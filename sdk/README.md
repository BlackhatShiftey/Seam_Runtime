# seam-client

Build custom agents with SEAM-backed long-term memory without embedding the
private SEAM runtime in your application.

`seam-client` is the public, Apache-2.0 Python SDK. It provides:

- synchronous and asynchronous clients
- `remember`, `recall`, and context assembly
- framework-neutral before-turn and after-turn agent hooks
- typed, opaque response models
- bearer-token authentication and explicit error types

It does **not** contain the private SEAM runtime, MIRL implementation, HS/1
surface codecs, storage engine, ranking logic, benchmark holdouts, or model
orchestration internals.

## Install

```bash
python -m pip install seam-client
```

Version 0.1.0 is the first public alpha release. To install directly from the
public source repository instead:

```bash
python -m pip install \
  "seam-client @ git+https://github.com/BlackhatShiftey/Seam_Runtime.git@main#subdirectory=sdk"
```

## Use it in an agent

```python
from seam_client import AgentMemory, SeamClient

client = SeamClient(
    base_url="http://127.0.0.1:8765",
    api_key="your-seam-token",
)
memory = AgentMemory(
    client=client,
    namespace="research-agent",
    session_id="thread-42",
    agent_id="researcher",
)

messages = [{"role": "user", "content": "What did we decide about licensing?"}]
messages = memory.augment_messages(
    messages,
    user_input=messages[-1]["content"],
)

# Call your preferred model/provider with `messages`.
assistant_output = "We separated the public SDK from the private runtime."

memory.after_turn(messages[-1]["content"], assistant_output)
```

`AgentMemory` does not choose or call a model. It supplies memory hooks that can
wrap your own OpenAI, Anthropic, local-model, or custom agent loop.

## Direct client

```python
from seam_client import SeamClient

with SeamClient.from_env() as seam:
    seam.remember(
        "The operator prefers evidence-backed answers.",
        namespace="my-agent",
        session_id="thread-42",
    )
    recalled = seam.recall(
        "answer style",
        namespace="my-agent",
        session_id="thread-42",
    )
    for memory in recalled.memories:
        print(memory.text, memory.score)
```

Environment variables:

- `SEAM_BASE_URL` — defaults to `http://127.0.0.1:8765`
- `SEAM_API_TOKEN` — optional bearer token for the configured server

## Async client

```python
from seam_client import AsyncAgentMemory, AsyncSeamClient

async with AsyncSeamClient.from_env() as client:
    memory = AsyncAgentMemory(
        client=client,
        namespace="async-agent",
        session_id="thread-7",
    )
    context = await memory.before_turn("What should I remember?")
```

## Partitions

- `namespace` isolates one agent or application from another.
- `session_id` isolates a specific conversation or run.
- `scope` is semantic and defaults to `thread`. Supported server scopes are
  `ephemeral`, `global`, `org`, `project`, `thread`, and `user`.

The server maps public partitions into an SDK-only internal namespace. Public
responses use opaque `rcpt_...` and `mem_...` identifiers.

## Hosted access

The SDK is public. A hosted SEAM endpoint is not implied by installing it.
Use a SEAM server URL and token you have been given, or run an authorized local
SEAM server. Hosted access remains separately provisioned.
