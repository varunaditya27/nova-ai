# Layer 8, Sub-Component: Tool Manager
#
# Responsibility: Orchestrate the complete tool use workflow.
# Entry point for all tool interactions.
#
# Workflow:
#   1. Detect tool intent from user message
#   2. Resolve any missing parameters (single clarifying question if needed)
#   3. Evaluate risk and determine confirmation tier
#   4. Get user confirmation (auto/soft/hard)
#   5. Execute tool action
#   6. Record outcome and link to episodic memory
#
# Main functions:
#   - process_tool_intent(user_message, context) -> ToolResult
#   - execute_tool(tool_name, action_type, parameters) -> ToolResult
#   - stream_tool_execution(tool_name, ...) -> AsyncGenerator[ExecutionEvent]
#
# Integration:
#   - Called during Layer 4 response generation when tool use is detected
#   - Calls plugins via base_plugin.ToolPlugin interface
#   - Records all actions via action_recorder.py
#   - Returns action results to Layer 4 for inclusion in response
#
# Design: Tool manager is the gatekeeper. It doesn't perform actions directly;
# it orchestrates plugins, which are the actual integrations.
