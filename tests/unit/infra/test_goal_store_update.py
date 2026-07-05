from backend.layer7_goals.goal_store import GoalStore
from backend.layer7_goals.schemas import Goal


def test_update_goal_replaces_by_id_and_appends_if_absent():
    store = GoalStore()
    g = Goal(goal_id="g1", title="old")
    store.add_goal(g)
    store.update_goal(Goal(goal_id="g1", title="new"))
    assert len(store.goals) == 1 and store.get("g1").title == "new"
    store.update_goal(Goal(goal_id="g2", title="fresh"))
    assert len(store.goals) == 2
