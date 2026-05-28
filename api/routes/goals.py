# Goals Routes
#
# Responsibility: Goal CRUD and task management.
#
# Endpoints:
#   - GET /goals: List all user goals
#   - POST /goals: Create new goal
#   - GET /goals/{id}: Retrieve goal details
#   - PATCH /goals/{id}: Update goal state
#   - DELETE /goals/{id}: Archive/delete goal
#   - GET /goals/{id}/tasks: List tasks for goal
#   - POST /goals/{id}/tasks: Create task
#
# All operations go through Layer 7 goal lifecycle.
