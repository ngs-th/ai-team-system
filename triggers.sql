-- Database triggers to maintain data integrity
-- Run: sqlite3 team.db < triggers.sql

-- Reset started_at when task goes back to todo
CREATE TRIGGER IF NOT EXISTS tr_reset_started_at_on_todo
AFTER UPDATE OF status ON tasks
FOR EACH ROW
WHEN NEW.status = 'todo' AND OLD.status != 'todo'
BEGIN
    UPDATE tasks SET started_at = NULL WHERE id = NEW.id;
END;

-- Reset started_at when task is assigned to new agent
CREATE TRIGGER IF NOT EXISTS tr_reset_started_at_on_assign
AFTER UPDATE OF assignee_id ON tasks
FOR EACH ROW
WHEN NEW.assignee_id != OLD.assignee_id OR (NEW.assignee_id IS NOT NULL AND OLD.assignee_id IS NULL)
BEGIN
    UPDATE tasks SET started_at = NULL, status = 'todo' WHERE id = NEW.id;
END;

-- Ensure actual_duration is calculated when completing
CREATE TRIGGER IF NOT EXISTS tr_calc_duration_on_complete
AFTER UPDATE OF status ON tasks
FOR EACH ROW
WHEN NEW.status = 'done' AND OLD.status != 'done' AND OLD.started_at IS NOT NULL
BEGIN
    UPDATE tasks SET 
        actual_duration_minutes = ROUND((strftime('%s', 'now') - strftime('%s', OLD.started_at)) / 60),
        completed_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

SELECT 'Triggers created successfully' as status;
