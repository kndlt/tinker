# Phase 6.1

Study and write a document about current state of the code base.

## `main()`

The entrypoint `main()` - It uses docker_manager to make sure docker container is running.

Then, it branches into `single_task_mode` and `interactive_chat_mode`.

Thoughts:
- [ ] We can probably remove the `single_task_mode` for now. to reduce the duplication. When task argument is given, we can make it as a first user message.

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
- [ ] Understand what TinkerWorkflow does.
- [ ] TinkerWorkflow doesn't seem to do anything.

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
- [ ] What does ContinuousAgentState contain?
- [ ] Do we really need all 4 nodes? Why don't we just embed this into the prompt without creating explicit states. It makes things less flexible, doesn't it?
- [ ] What is current_phase and why do we transition to "decide" when current phase is "decide"?
- [ ] Act transitions to `observe`. Why?

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
- [ ] Is it okay that it only produces a shell command? Should it produce some reasoning and just encode the shell command inside a block or something?
- [ ] Can we add an option to run python commands as well?
- [ ] What is an example output of this step and is there reason why we don't have any examples in this prompt?
- [ ] The response is either shell command or `NO_ACTION`. This seems restrictive. 
- [ ] Do we really need these nodes? What is the benefit of using these nodes? Can we just make it into a one node? I'm ready to be convinced but I want some justification.

### `observe_node`

Next state is `observe_node`. This node is supposed to observe and analyze results. It will look into `last_result`'s stdout and stderr. Also will read `success` which tells whether the operation succeeded or not.

It will then update the `working_memory` with `last_command_success` to be true or false.

Then, right away move on to `decide` phase.

Thoughts:
- [ ] Does this node do anything other than updating working_memory? Wouldn't it be simpler to merge this and act state
- [ ] Shouldn't observe node utilize LLM to really do the "observing"?

### `decide_node`

Finally, `decide_node` checks if max_iteration is reached. If it did, we set `should_continue` to false.

If we have `exit_reason`, we exit with that messaging.

Otherwise, we will just continue to looping incrementing the iteration count.

Thoughts:
- [ ] Agent is aware of maximum number of iterations. What does this mean?
- [ ] Can we have sub-routines? Like the main agent is the orchestrator and it spawns sub-routines to get answers. Or are we effectively doing sub-routines already?
- [ ] Shouldn't this node use LLM to decide what to do rather than control flow?