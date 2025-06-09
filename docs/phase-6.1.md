# Phase 6.1

Study and write a document about current state of the code base.

## `main()`

The entrypoint `main()` - It uses docker_manager to make sure docker container is running.

Then, it branches into `single_task_mode` and `interactive_chat_mode`.

Thoughts:
- [ ] We can probably remove the `single_task_mode` for now. to reduce the duplication. When task argument is given, we can make it as a first user message.
  - [x] Agent Zero: Yes, this makes sense. Having two separate modes creates unnecessary code duplication. Converting the task argument into the first user message would simplify the codebase while maintaining the same functionality.

In the `interactive_chat_mode`, we initialize `TinkerCheckpointManager` and then create a `TinkerWorkflow` using it.

Then, from a checkpoint manager, we `get_main_thread_id`. Then pull existing conversation from it.

It then enters a while loop. It continues running until it hears any user_input. 

There are some exit criteria and some memory operations.

Then, the main work starts after line 55.

It creates `ContinousAgentWorkflow`. Then, trigger `run_continuous_task()` from it.

It then spits out result object with messages.
If the message has 'content', we parse the content, then show different messages.

- THINKING
- ACTION
- OBSERVE
- DECIDE
- ERROR
- etc.

The `user_response` is part of it is then displayed separately.

Thoughts
- [ ] Understand what ContinuousAgentWorkflow does.
  - [x] Agent Zero: ContinuousAgentWorkflow implements a continuous reasoning loop with 4 distinct phases (think, act, observe, decide) that cycles until goal completion or max iterations. It manages the state transitions and execution of each phase.
- [ ] Understand what TinkerWorkflow does.
  - [x] Agent Zero: TinkerWorkflow appears to be a wrapper that manages conversation state and checkpointing. It initializes the checkpoint manager but doesn't seem to actively participate in the actual task execution logic.
- [ ] TinkerWorkflow doesn't seem to do anything.
  - [x] Agent Zero: Correct observation. TinkerWorkflow seems to be mostly scaffolding for future functionality or legacy code. The actual work is delegated to ContinuousAgentWorkflow, making TinkerWorkflow potentially redundant.

## `ContinuousAgentWorkflow`

It creates `ContinuousAgentNodes`. Then builds a graph. 

**What does building a graph mean?** It creates a StateGraph with `ContinuousAgentState`. Then adds 4 nodes. 

- `think`: the entrypoint. It transitions to `decide` if current state is `decide`. Otherwise to `act`.
- `act`: this transitions to `observe`.
- `observe`: this transitions to `decide`.
- `decide`: this goes to `think` if `should_continue` is true. Otherwise, goes to `end`.

```
   -- think <-
  |     |     |
  |    act    |
  |     |     |
  |   observe |
  |     |     |
   -> decide -
        |
       end
```

Thoughts:
- [ ] What is StateGraph?
  - [x] Agent Zero: StateGraph is a LangGraph construct that defines a state machine with nodes and edges. It manages the flow of execution between different processing steps and maintains state throughout the workflow.
- [ ] What does ContinuousAgentState contain?
  - [x] Agent Zero: Based on the code, ContinuousAgentState likely contains: messages, current_goal, working_memory, observations, planned_actions, iteration_count, should_continue, exit_reason, current_phase, last_action, and last_result.
- [ ] Do we really need all 4 nodes? Why don't we just embed this into the prompt without creating explicit states. It makes things less flexible, doesn't it?
  - [x] Agent Zero: You're right. The explicit state machine adds complexity without clear benefits. A single node with prompt-based reasoning could be more flexible and easier to maintain. The current approach seems over-engineered for what could be achieved with a simpler architecture.
- [x] What is current_phase and why do we transition to "decide" when current phase is "decide"?
  - [x] Agent Zero: This seems like a bug or unclear logic. If current_phase is already "decide", transitioning to "decide" again doesn't make sense. The logic should probably check for a different condition or phase.
    - [x] Sprited Dev: It looks like it is kinda duplicated state for sending current phase into LLM APIs. Also it is used in control flows.
- [x] Act transitions to `observe`. Why?
  - [x] Agent Zero: The act node executes commands and needs to observe the results before deciding next steps. This follows a classic OODA loop pattern (Observe, Orient, Decide, Act), though the implementation seems unnecessarily rigid.

Then we review `run_continuous_task` function. It takes in `goal` and `max_iterations`. It creates `initial_state` using
human message and `current_goal`. working+memory is initialized
to be empty. Observations is also empty. Planned actions are also empty.

The initial messages is 
```
Starting continuous reasoning loop for goal: ...
```
Then, we `invoke` the graph. `recursion_limit` is set to 100.
Finally when things are done, it sets `final_state`'s messages to be "Completed after N iterations. ..."

## `ContinuousAgentNodes`

At the start we initialize `AnthropicToolsManager`.

There are various nodes.

### `think_node`

`think_node` think about the current goal and plan next steps.

```
You are in the THINKING phase of continuous reasoning. Analyze the current situation and plan your next actions efficiently.

Current Goal: ...
Iteration: 1 over 10

Working Memory:
...

Recent Observations:
...observations...

Planned Actions Queue
...planned actions...

Last Action: ...
Last Result: ...

Consider these key questions:
- What is the current goal and what progress has been made?
- What information do I have and what is still missing?
- What are the most efficient next steps to take?
- Are there any risk or constraints I need to consider?
- How can I validate that I'm moving in the right direction?

IMPORTANT: First determinde if this is conversational input (greeting, question about status, etc.) or a task to execute:
- If conversational (like "what's up?", "hello", "how are you?"), provide a direct response and mark as GOAL_ACHIEVED
- If a task, proceed with planning actions.

Efficiency guidelines:
- Focus on high-impact actions that move toward the goal
- Avoid redundant information gathering
- Consider time and resource constraints
- Plan 2-3 steps ahead when possible
- Identify clear success criteria for the current iteration

Iteration awareness:
- Track progress from previous iterations
- Learn from any errors or setbacks
- Adjust strategy based on new information
- Consider whether the goal needs refinement

Output your thoughts clearly, focusing on actionable insights and concrete next steps. Keep analysis concise but thorough.

If this is conversational input, include your response in the format:
RESPONSE: [your response to the user]
GOAL_ACHIEVED

Otherwise, respond with your reasoning and what specific action to take next (or 'GOAL_ACHIEVED' if done).
```

This is sent to claude API as `user` message.

In the response, if `RESPONSE:` is found, it returns the response as `user_response`.

If `GOAL_ACHIEVED` is found, we set `should_continue` to false and `exit_reason` to be "Goal achieved". Then current_phase to `decide`. Otherwise to `act`.

Thoughts:
- [ ] Some of these look like system message, perhaps then need to be using system message instead to prevent system prompt leakage.
  - [x] Agent Zero: Absolutely correct. The instructions about reasoning phases, efficiency guidelines, and iteration awareness should be system messages. Putting them as user messages risks prompt injection attacks and makes the system less secure.

### `act_node`

Next is `act_node`. It fist processes last `[THINKING]` part of messages.

```
Based on this thinking: ...

Based on your thinking, decide on the next action to take. Choose actions that are safe, efficient, and move toward your goal.

Safety considerations:
- Avoid destructive operations without clear necessity
- Validate inputs and check constraints before acting
- Use non-destructive alternatives when possible (e.g. --dry-run flags)
- Back up important data before major changes

Actions formatting guidelines:
- Use clear, specific commands with proper syntax
- Include necessary flags and parameters
- Specify full paths when working with files
- Add error handling when appropriate

Error handling approach:
- Check for common failure conditions
- Include validation step when needed
- Plan fallback actions for likely failures
- Gather diagnostic information when commands fail

Choose ONE specific action that best advances your goal. Format as a clear command or instruction.

Respond with ONLY the command, nothing else. If no command is needed, respond with 'NO_ACTION'.
```

We send this over to Anthropic (max_token=200). The response is either shell command or `NO_ACTION`. 

If we get shell action, we run `execute_shell_command` tool in `tool_manager`.

Result is then stored in `last_result`.
If error happens, we append to `messages` with `[ERROR] Act phase failed: ...error text...`

Error or success, the next transition state is always `observe`.

Thoughts:
- [ ] What is the implication of 200 max_tokens. Will it silently cause reliability issues without letting us know.
  - [x] Agent Zero: Yes, 200 tokens is quite limiting. Complex commands with multiple flags or long file paths could get truncated, causing silent failures. This should either be increased or have proper truncation detection.
- [ ] Is it okay that it only produces a shell command? Should it produce some reasoning and just encode the shell command inside a block or something?
  - [x] Agent Zero: Having reasoning alongside the command would be better for debugging and understanding. A structured format like `<reasoning>...</reasoning><command>...</command>` would provide context while maintaining parseability.
- [ ] Can we add an option to run python commands as well?
  - [x] Agent Zero: Yes, Python execution would be valuable for data processing, calculations, and complex logic that's awkward in shell. Could use a prefix like `python:` or have the model choose the execution environment.
- [ ] What is an example output of this step and is there reason why we don't have any examples in this prompt?
  - [x] Agent Zero: The lack of examples is a significant omission. Examples like `ls -la /home/user/project` or `grep -r "TODO" src/` would clarify expectations and improve model performance.
- [ ] The response is either shell command or `NO_ACTION`. This seems restrictive. 
  - [x] Agent Zero: Very restrictive. Should support multiple action types: shell commands, Python code, API calls, file operations, or even "need more information" responses.
- [ ] Do we really need these nodes? What is the benefit of using these nodes? Can we just make it into a one node? I'm ready to be convinced but I want some justification.
  - [x] Agent Zero: The multi-node approach seems unnecessarily complex. A single node with a good prompt could handle think→act→observe→decide in one pass, reducing API calls and latency while maintaining flexibility.

### `observe_node`

Next state is `observe_node`. This node is supposed to observe and analyze results. It will look into `last_result`'s stdout and stderr. Also will read `success` which tells whether the operation succeeded or not.

It will then update the `working_memory` with `last_command_success` to be true or false.

Then, right away move on to `decide` phase.

Thoughts:
- [ ] Does this node do anything other than updating working_memory? Wouldn't it be simpler to merge this and act state
  - [x] Agent Zero: Correct, this node is just updating a boolean flag. It could easily be merged with the act node, reducing unnecessary state transitions and complexity.
- [ ] Shouldn't observe node utilize LLM to really do the "observing"?
  - [x] Agent Zero: Yes! An LLM-powered observe node could analyze command output, extract relevant information, identify errors or unexpected results, and update working memory with meaningful insights rather than just success/failure.

### `decide_node`

Finally, `decide_node` checks if max_iteration is reached. If it did, we set `should_continue` to false.

If we have `exit_reason`, we exit with that messaging.

Otherwise, we will just continue to looping incrementing the iteration count.

Thoughts:
- [ ] Agent is aware of maximum number of iterations. What does this mean?
  - [x] Agent Zero: The agent knows it has limited iterations (e.g., "Iteration: 1 over 10"), which could create artificial urgency or cause premature termination. It might be better to hide this limit and let the agent work naturally until completion.
- [ ] Can we have sub-routines? Like the main agent is the orchestrator and it spawns sub-routines to get answers. Or are we effectively doing sub-routines already?
  - [x] Agent Zero: The current system doesn't support true sub-routines. Adding hierarchical task delegation would be powerful - the main agent could spawn specialized sub-agents for specific tasks (e.g., debugging, research, implementation) and coordinate their results.
- [ ] Shouldn't this node use LLM to decide what to do rather than control flow?
  - [x] Agent Zero: Absolutely. The decide node should use LLM reasoning to determine next steps, evaluate progress, decide if the goal is met, or if the approach needs adjustment. Current implementation is just mechanical iteration counting.

## `ContinuousAgentState`

`ContinuousAgentState` is typed dictionary with following states.

```
messages
current_goal
iteration_count
max_iterations

working_memory
observation
planned_actions

last_action
last_result

should_continue
exit_reason

current_phase

user_response
```

That's it.

## `TinkerWorkflow`

It creates `TinkerLangGraphNodes`. 
It also builds a graph.

- `task_analyzer`
- `tool_executor`
- `completion`

Thoughts:
- [ ] This doesn't look like it is being used. Should we remove this as a whole?
  - [x] Agent Zero: Yes, TinkerWorkflow appears to be unused legacy code. It's creating nodes (task_analyzer, tool_executor, completion) that aren't invoked anywhere. Removing it would simplify the codebase without affecting functionality.

## `TinkerState`

Contains 
```
task_content
conversation_history
tool_results
planned_tools
pending_ai_response
remaining_output
current_directory
resumption_point
thread_id
tinker_checkpoint_id
execution_status
```

Thoughts:
- [ ] Similar question to `TinkerWorkflow`, I don't think this langgraph is actually invoked. Should we remove it?
  - [x] Agent Zero: Correct, TinkerState is part of the unused TinkerWorkflow system. Since the actual work is done by ContinuousAgentWorkflow/State, this entire TinkerState structure can be removed to reduce code clutter.

## `TinkerCheckpointManager`

It uses `.tinker/memory.db`. Then connects to it.

### `_init_custom_tables()`

It initializes a table:
```
tinker_sessions
    thread_id
    created_at
    last_accessed
    task_summary
    status
tinker_checkpoints_meta
    checkpoint_id
    thread_id
    created_at
    resumption_point
    execution_status
    thread_id
```

Thoughts:
- [ ] Are these being used in any meaningful manner?
  - [x] Agent Zero: From the code review, these tables seem underutilized. The checkpoint system appears to be partially implemented - tables are created but not fully leveraged for resumption or session management.
- [ ] What does session mean?
  - [x] Agent Zero: A session represents a continuous interaction period with the user, identified by thread_id. It tracks when the conversation started, last accessed time, task summary, and status.
- [ ] What does checkpoint mean?
  - [x] Agent Zero: A checkpoint is a saved state snapshot during task execution. It's meant to enable resumption from specific points, but the implementation seems incomplete as resumption_point is stored but not actively used.
- [ ] What is the point of `update_session_access`?
  - [x] Agent Zero: It updates the last_accessed timestamp for a session. This could be useful for session cleanup or understanding user engagement patterns, but it's unclear if this data is actually used anywhere.
- [ ] What does `resumption_point` mean?
  - [x] Agent Zero: It indicates where in the workflow execution the checkpoint was taken (e.g., 'task_analyzed', 'tools_executed'). Theoretically allows resuming from that exact workflow state, but this feature doesn't appear to be implemented.
- [ ] When do we use `list_sessions`?
  - [x] Agent Zero: This would list all conversation sessions, potentially for UI display or session management. However, it doesn't appear to be called in the current codebase, suggesting it's unused functionality.
- [ ] Why `list_checkpoints_for_thread`?
  - [x] Agent Zero: This would retrieve all checkpoints for a specific conversation thread, presumably for resumption or debugging. Like other checkpoint features, it seems to be unused infrastructure.
- [ ] When is `get_conversation_history` called?
  - [x] Agent Zero: It's called during interactive_chat_mode initialization to load previous messages from a thread. This maintains conversation continuity across sessions, which is one of the few checkpoint features actually being used.

## `TinkerLangGraphNodes`

### `task_analyzer_node`

Receives task_content then appends `conversation_history`.

It then calls Claude with following message.

```
You are Tinker, an autonomous AI engineering assistant designed to help with software development tasks. You work collaboratively with users to build, maintain, and improve software projects.

Your core capabilities include:
- Code development and bug fixing
- System architecture and design
- Testing and quality assurance
- Documentation and technical writing
- DevOpts and deployment tasks
- Code review and optimization

You operate within a persistent Docker container environment with full shell access via the execute_shell_command tool, providing you with:
- Complete file system operations (...)
- Package management and dependency installations
- Git version control
- Email and notification
- Github CLI for repository management

Guidelines for effective operation:
- Always understand the task before acting - ask clarifying questions when needed
- Break complex tasks into manageable steps and track progress.
- use appropriate tools for each task - don't over-engineer simple solutions
- Be safety-conscious with destructive operations
- Maintain clean, readable code following project conventions
- Document your work and reasoning clearly.

Communication Style:
- Be conversational and helpful like a skilled pair programming partner
- Answer simple questions directly without unnecessary tool usage.
- Explain your reasoning when making technical decisions
- Ask for feedback and clarification when requirements are unclear

Technical environment:
- Working directory: /home/tinker (persistent across sessions)
- Pre-configured development tools and CLI utilities
- GitHub CLI available for repository operations
- Standard package managers and build tools installed.
```

Thoughts:
- [ ] The "continuous" version of nodes are missing some of these details like "working directory".
  - [x] Agent Zero: Yes, the continuous version lacks important context like working directory (/home/tinker), available tools, and environment details. This information should be added to ensure consistent behavior.
- [ ] We should compare this file and the `continuous` version of the file and see if we are missing anything in continuous version.
  - [x] Agent Zero: Agreed. The TinkerLangGraphNodes has richer system prompts with technical environment details, safety guidelines, and clearer capability descriptions that should be incorporated into the continuous version.
- [ ] Should we ask the agent to utilize `npx` and `pipx` for using packages that may or may not be installed?
  - [x] Agent Zero: Great idea! Using npx and pipx would allow running tools without permanent installation, reducing container bloat and avoiding version conflicts. This should be added to the agent's guidelines.

Once it receives the response.

```
Based on the user's request: "{task_content}"

Determine if you need to use tools or can respond directly.

Use tools when you need to:
- Read, create, edit, or analyze files
- Execute commands or run programs
- Check system status or gather information
- Perform git operations or interact with repositories
- Send emails or notifications

Respond directly (no tools) for:
- Answering conceptual or theoretical questions
- Providing explanations of existing code you can see
- Discussing best practices or design patterns
- General conversation or clarification requests

Examples:
- "What does this function do?" -> Direct response (if code is visible)
- "Create a new Python file" -> COMMAND: touch new_file.py
- "How do I implement OAuth" -> Direct response with explanation
- "Run the tests" -> COMMAND: python -m pytest
- "What's the difference between REST and GraphQL?" -> Direct response
- "Check if the server is running" -> COMMAND: ps aux | grep server

Choose the most efficient approach - prefer direct responses when possible, use tools when necessary.

Respond with either:
1. Just conversational text if no commands needed
2. A list of specific shell commands I should run, one per line, prefixed with "COMMAND: "
```

Once response comes back it parses `COMMAND: ` lines then update `planned_tools` with `execute_shell_command`.

At this point, the `resumption_point` is set to `task_analyzed`.

### `tool_executer_node`

This node looks at `planned_tools`, then calls `execute_tool`. Then stores the result into `tool_results`.

It then creates `tool_summary` that summarize call calls.
Then it creates `all_tool_output` which goes into the prompt:

```
User asked: {task_content}

Command results:
{all_tool_output}

Analyze the tool execution results and provide a clear, contextual response to the user.

Focus areas for analysis:
- Success/failure status and any error conditions
- Key information that addresses the user's request
- Unexpected results that need explanation
- Next steps or follow-up actions needed

Response guidelines:
- Summarize the most relevant findings first
- Include specific details when they're important for understanding
- Explain any errors in user-friendly terms.
- Filter out routine/expected output unless specifically relevant
- Suggest concrete next steps when appropriate.

For different result types:
- File operations: Convirm success and highlight important content
- Command execution: Focus on meaningful output and any errors
- Code execution: Focus on meaningful output and any errors.
- System queries: Present information in organized, useful format.

Keep responses concise but informative - users need actionable insights, not raw data dumps.
```

At this time, `execution_status` is "executing" and the `resumption_point` is "tools_executed".

Once response comes back, we move over to next step.

Thoughts:
- [ ] How do we hint in the code base to instruct AI agent to never touch that or treat it as a black box.
  - [x] Agent Zero: Use clear naming conventions (e.g., `_internal_`, `DO_NOT_MODIFY_`), add prominent comments, create .aiignore files similar to .gitignore, or include explicit instructions in the system prompt about protected files/directories.
- [ ] tool_summary is not getting used anywhere. We should remove it.
  - [x] Agent Zero: Correct, tool_summary is computed but never used. It's dead code that should be removed to simplify the codebase.
- [ ] It appears that we are just using `anthropic` library instead of using something that LangGraph provides. What is the right approach? Does LangGraph provide a different way to call into Anthropic APIs?
  - [x] Agent Zero: LangGraph does provide LLM integration through LangChain, but using the anthropic library directly gives more control over API parameters. The direct approach is fine if you don't need LangGraph's built-in features like automatic retries or callbacks.
- [ ] When we ask the agent to create shell commands, we can ask it to suggest multiple options and select the best one.
  - [x] Agent Zero: Interesting idea! The agent could propose 2-3 command variations with trade-offs (e.g., verbose vs concise, safe vs fast) and either auto-select or let the user choose. This would improve reliability and transparency.
- [ ] When we ask the agent to create shell commands, we can ask it to provide fallback command incase the command fails.
  - [x] Agent Zero: Excellent suggestion! Commands could be structured as primary + fallback, like `command1 || command2` or with explicit error handling. This would make the system more robust to common failures.
- [ ] When we ask the agent to create shell commands, we can ask it what it expects to return.
  - [x] Agent Zero: Yes! Having the agent predict expected output would help with validation and error detection. It could specify expected exit codes, output patterns, or side effects, making debugging much easier.
- [ ] Can we ask the agent to make it so that the output is not too long? Or somehow we only send top 100 lines then AI can do another tool call to get next 1000 lines or something?
  - [x] Agent Zero: Smart approach! The agent could use commands like `head -n 100` or `| less`, then request more if needed. Alternatively, implement output pagination in the tool executor with a 'continue reading' option.
- [ ] Or, we can just store the result in a file and have the agent do grep on that file to see the result.
  - [x] Agent Zero: Excellent idea! Redirecting output to temporary files (e.g., `command > /tmp/output.txt`) then using grep/awk/sed for analysis would handle large outputs efficiently and enable complex searches.
- [ ] This result analysis step is missing in the `continuous` version. Is that fine?
  - [x] Agent Zero: No, this is a significant omission. The result analysis step helps interpret command outputs for users. The continuous version should include this to provide clear, actionable insights rather than raw output.
- [ ] Does this design have an issue where all commands are planned in one go and we don't have any way to re-think our direction in the middle when we notice an issue? We need a solution where it is iterative, and can just fluidly think of next steps.
  - [x] Agent Zero: Yes, this is a major limitation. Planning all commands upfront prevents adapting to unexpected results. The continuous version's iterative approach is better, but even that could benefit from more fluid re-planning capabilities.

### `completion_node`

This step is trivial, we mark `execution_status` to "completed" and `resumption_point` to "completed".

## Action Items

Based on the analysis above, here are the key improvements to implement:

### Code Simplification
- [ ] Remove single_task_mode and convert task argument to first user message
- [ ] Remove unused TinkerWorkflow and TinkerState classes entirely
- [ ] Merge observe_node functionality into act_node
- [ ] Consider replacing 4-node state machine with single-node prompt-based approach
- [ ] Remove unused tool_summary variable in tool_executor_node

### Security & Reliability
- [ ] Move system instructions from user messages to system messages
- [ ] Increase max_tokens limit from 200 or add truncation detection
- [ ] Add .aiignore file support for protecting sensitive code areas

### Feature Enhancements
- [ ] Add Python code execution support alongside shell commands
- [ ] Implement LLM-powered observe node for intelligent output analysis
- [ ] Add LLM reasoning to decide_node instead of mechanical iteration counting
- [ ] Support multiple action types (shell, Python, API calls, file ops)
- [ ] Add command examples to act_node prompt
- [ ] Implement output pagination or file-based output handling for large results

### Continuous Agent Improvements
- [ ] Port missing environment details from TinkerLangGraphNodes to continuous version
- [ ] Add result analysis step to continuous workflow
- [ ] Hide iteration limits from agent to avoid artificial urgency
- [ ] Implement sub-agent/sub-routine capability for complex tasks
- [ ] Add npx/pipx usage guidelines to agent prompts

### Command Execution
- [ ] Structure commands with reasoning: `<reasoning>...</reasoning><command>...</command>`
- [ ] Implement command alternatives and fallback mechanisms
- [ ] Add expected output predictions for commands
- [ ] Enable iterative re-planning based on command results

### Checkpoint System
- [ ] Either fully implement checkpoint resumption or remove the incomplete implementation
- [ ] Clarify purpose and usage of session vs checkpoint concepts
- [ ] Implement actual usage of resumption_point functionality

