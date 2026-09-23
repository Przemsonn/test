-- ================================================================
-- Shared GitHub Desktop workshop SQL file
-- Dialect: PostgreSQL
-- Purpose: practice commits, branches, pull requests, reviews and merges
-- ================================================================

BEGIN;

-- ----------------------------------------------------------------
-- 1. Clean setup
-- ----------------------------------------------------------------
DROP VIEW IF EXISTS vw_task_progress;
DROP TABLE IF EXISTS task_comments;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS participants;

-- ----------------------------------------------------------------
-- 2. Core tables
-- ----------------------------------------------------------------
CREATE TABLE participants (
    participant_id      INTEGER PRIMARY KEY,
    initials            VARCHAR(1000) NOT NULL UNIQUE,
    display_name        VARCHAR(10000) NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    project_id          INTEGER PRIMARY KEY,
    project_name        VARCHAR(150) NOT NULL,
    start_date          DATE NOT NULL,
    target_end_date     DATE NOT NULL,
    CONSTRAINT chk_project_dates CHECK (target_end_date >= start_date)
);

CREATE TABLE tasks (
    task_id             INTEGER PRIMARY KEY,
    project_id          INTEGER NOT NULL REFERENCES projects(project_id),
    participant_id      INTEGER NOT NULL REFERENCES participants(participant_id),
    task_name           VARCHAR(200) NOT NULL,
    category            VARCHAR(50) NOT NULL,
    priority            VARCHAR(10) NOT NULL,
    status              VARCHAR(20) NOT NULL,
    start_date          DATE NOT NULL,
    due_date            DATE NOT NULL,
    completed_date      DATE,
    estimated_hours     NUMERIC(8, 2) NOT NULL,
    actual_hours        NUMERIC(8, 2),
    completion_pct      NUMERIC(5, 2) NOT NULL DEFAULT 0,
    notes               VARCHAR(500),
    CONSTRAINT chk_task_dates CHECK (due_date >= start_date),
    CONSTRAINT chk_priority CHECK (priority IN ('High', 'Medium', 'Low')),
    CONSTRAINT chk_status CHECK (status IN ('Not Started', 'In Progress', 'Blocked', 'Completed')),
    CONSTRAINT chk_completion CHECK (completion_pct BETWEEN 0 AND 1),
    CONSTRAINT chk_hours CHECK (estimated_hours >= 0 AND (actual_hours IS NULL OR actual_hours >= 0))
);

CREATE TABLE task_comments (
    comment_id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id             INTEGER NOT NULL REFERENCES tasks(task_id),
    participant_id      INTEGER NOT NULL REFERENCES participants(participant_id),
    comment_text        VARCHAR(500) NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------
-- 3. Sample data
-- ----------------------------------------------------------------
INSERT INTO participants (participant_id, initials, display_name)
VALUES
    (0, 'PRKD', 'Workshop Participant 1'),
    (2, 'PAAT', 'Workshop Participant 2'),
    (3, 'ALZK', 'Workshop Participant 3'),
    (4, 'WERA', 'Workshop Participant 4'),
    (5, 'DADY', 'Workshop Participant 5'),
    (6, 'MIWW', 'Workshop Participant 6'),
    (7, 'KIPJ', 'Workshop Participant 7'),
    (8, 'KRWO', 'Workshop Participant 8');

INSERT INTO projects (project_id, project_name, start_date, target_end_date)
VALUES
    (1, 'Sales Dashboard Refresh', DATE '2026-09-01', DATE '2026-10-31'),
    (2, 'Data Quality Automation', DATE '2026-09-01', DATE '2026-10-31'),
    (3, 'Monthly Reporting Workflow', DATE '2026-09-01', DATE '2026-10-31'),
    (4, 'GitHub Workshop Materials', DATE '2026-09-01', DATE '2026-10-31');

INSERT INTO tasks (
    task_id,
    project_id,
    participant_id,
    task_name,
    category,
    priority,
    status,
    start_date,
    due_date,
    completed_date,
    estimated_hours,
    actual_hours,
    completion_pct,
    notes
)
VALUES
    (101, 1, 1, 'Prepare source data model', 'SQL', 'High', 'Completed', DATE '2026-09-01', DATE '2026-09-04', DATE '2026-09-04', 6.00, 6.50, 1.00, 'Initial model approved'),
    (102, 1, 1, 'Create KPI validation query', 'SQL', 'High', 'In Progress', DATE '2026-09-08', DATE '2026-09-25', NULL, 5.00, 3.00, 0.60, 'Add edge-case tests'),
    (103, 4, 1, 'Review workshop repository', 'Testing', 'Medium', 'Not Started', DATE '2026-09-24', DATE '2026-09-30', NULL, 3.00, NULL, 0.00, 'Check branches and permissions'),
    (104, 2, 2, 'Define duplicate detection rules', 'Documentation', 'Medium', 'Completed', DATE '2026-09-02', DATE '2026-09-05', DATE '2026-09-05', 4.00, 3.50, 1.00, 'Rules saved in project notes'),
    (105, 2, 2, 'Build duplicate records query', 'SQL', 'High', 'In Progress', DATE '2026-09-07', DATE '2026-09-24', NULL, 7.00, 5.50, 0.80, 'Waiting for one source column'),
    (106, 4, 2, 'Add README examples', 'Documentation', 'Low', 'Not Started', DATE '2026-09-25', DATE '2026-10-02', NULL, 2.00, NULL, 0.00, 'Use simple Markdown examples'),
    (107, 3, 3, 'Map monthly input files', 'Excel', 'Medium', 'Completed', DATE '2026-09-01', DATE '2026-09-03', DATE '2026-09-02', 3.00, 2.50, 1.00, 'File map shared with team'),
    (108, 3, 3, 'Create import checklist', 'Documentation', 'Medium', 'Completed', DATE '2026-09-04', DATE '2026-09-08', DATE '2026-09-09', 3.00, 4.00, 1.00, 'Completed one day late'),
    (109, 4, 3, 'Test merge conflict scenario', 'Testing', 'High', 'In Progress', DATE '2026-09-21', DATE '2026-09-24', NULL, 4.00, 2.00, 0.50, 'Use shared SQL file'),
    (110, 1, 4, 'Design dashboard layout', 'Power BI', 'Medium', 'Completed', DATE '2026-09-03', DATE '2026-09-08', DATE '2026-09-08', 6.00, 6.00, 1.00, 'Layout accepted'),
    (111, 1, 4, 'Configure drill-through page', 'Power BI', 'Medium', 'Blocked', DATE '2026-09-09', DATE '2026-09-22', NULL, 5.00, 2.00, 0.40, 'Blocked by missing relationship'),
    (112, 4, 4, 'Update workshop screenshots', 'Documentation', 'Low', 'Not Started', DATE '2026-09-25', DATE '2026-10-01', NULL, 3.00, NULL, 0.00, 'Capture GitHub Desktop screens'),
    (113, 2, 5, 'Create data quality test cases', 'Testing', 'High', 'Completed', DATE '2026-09-02', DATE '2026-09-09', DATE '2026-09-08', 5.00, 5.00, 1.00, 'All expected outcomes documented'),
    (114, 2, 5, 'Automate exception summary', 'Python', 'High', 'In Progress', DATE '2026-09-10', DATE '2026-09-26', NULL, 8.00, 4.00, 0.55, 'Prototype creates CSV output'),
    (115, 3, 5, 'Validate report totals', 'Excel', 'Medium', 'Not Started', DATE '2026-09-24', DATE '2026-09-29', NULL, 4.00, NULL, 0.00, 'Compare with prior month'),
    (116, 3, 6, 'Create monthly control sheet', 'Excel', 'High', 'Completed', DATE '2026-09-01', DATE '2026-09-07', DATE '2026-09-07', 6.00, 6.50, 1.00, 'Includes reconciliation section'),
    (117, 3, 6, 'Add formula error checks', 'Excel', 'High', 'In Progress', DATE '2026-09-08', DATE '2026-09-23', NULL, 5.00, 4.00, 0.75, 'Two checks remain'),
    (118, 4, 6, 'Create sample pull request', 'Git', 'Medium', 'Completed', DATE '2026-09-18', DATE '2026-09-21', DATE '2026-09-20', 2.00, 1.50, 1.00, 'Pull request merged'),
    (119, 1, 7, 'Prepare dashboard test data', 'SQL', 'Medium', 'Completed', DATE '2026-09-04', DATE '2026-09-10', DATE '2026-09-10', 4.00, 4.00, 1.00, 'Includes null and duplicate rows'),
    (120, 1, 7, 'Run user acceptance test', 'Testing', 'High', 'In Progress', DATE '2026-09-15', DATE '2026-09-28', NULL, 6.00, 2.50, 0.35, 'First feedback collected'),
    (121, 2, 7, 'Document exception handling', 'Documentation', 'Low', 'Not Started', DATE '2026-09-28', DATE '2026-10-05', NULL, 3.00, NULL, 0.00, 'Add examples after testing'),
    (122, 2, 8, 'Profile source columns', 'SQL', 'Medium', 'Completed', DATE '2026-09-01', DATE '2026-09-06', DATE '2026-09-06', 5.00, 4.50, 1.00, 'Profile stored in workbook'),
    (123, 3, 8, 'Prepare refresh instructions', 'Documentation', 'Medium', 'In Progress', DATE '2026-09-12', DATE '2026-09-25', NULL, 4.00, 2.50, 0.65, 'Add troubleshooting section'),
    (124, 4, 8, 'Verify final workshop files', 'Testing', 'High', 'Blocked', DATE '2026-09-22', DATE '2026-09-23', NULL, 3.00, 1.00, 0.25, 'Waiting for final participant list');

INSERT INTO task_comments (task_id, participant_id, comment_text)
VALUES
    (102, 1, 'Added validation for missing KPI values.'),
    (105, 2, 'Duplicate logic reviewed with the process owner.'),
    (111, 4, 'Relationship issue reproduced in the test model.'),
    (114, 5, 'Python prototype exports the exception summary.'),
    (124, 8, 'Final verification will continue after files are updated.');

COMMIT;

-- ----------------------------------------------------------------
-- 4. Basic selections
-- ----------------------------------------------------------------
SELECT
    task_id,
    task_name,
    status,
    priority,
    due_date
FROM tasks
ORDER BY due_date, priority;

SELECT
    task_id,
    task_name,
    estimated_hours,
    actual_hours,
    actual_hours - estimated_hours AS variance_hours
FROM tasks
WHERE actual_hours IS NOT NULL
ORDER BY variance_hours DESC;

-- ----------------------------------------------------------------
-- 5. Joins: readable task list
-- ----------------------------------------------------------------
SELECT
    t.task_id,
    p.initials AS owner,
    pr.project_name,
    t.task_name,
    t.category,
    t.priority,
    t.status,
    t.due_date,
    t.completion_pct
FROM tasks t
JOIN participants p
    ON p.participant_id = t.participant_id
JOIN projects pr
    ON pr.project_id = t.project_id
ORDER BY pr.project_name, p.initials, t.task_id;

-- ----------------------------------------------------------------
-- 6. Aggregation by status and priority
-- ----------------------------------------------------------------
SELECT
    status,
    COUNT(*) AS task_count,
    ROUND(AVG(completion_pct) * 100, 1) AS average_completion_pct,
    SUM(estimated_hours) AS total_estimated_hours,
    SUM(COALESCE(actual_hours, 0)) AS total_actual_hours
FROM tasks
GROUP BY status
ORDER BY task_count DESC, status;

SELECT
    priority,
    COUNT(*) AS task_count,
    COUNT(*) FILTER (WHERE status = 'Completed') AS completed_count,
    COUNT(*) FILTER (WHERE status = 'Blocked') AS blocked_count
FROM tasks
GROUP BY priority
ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;

-- ----------------------------------------------------------------
-- 7. CTE: schedule health as of the workshop reference date
-- ----------------------------------------------------------------
WITH task_health AS (
    SELECT
        t.*,
        CASE
            WHEN t.status = 'Completed' AND t.completed_date <= t.due_date THEN 'Completed on time'
            WHEN t.status = 'Completed' AND t.completed_date > t.due_date THEN 'Completed late'
            WHEN t.status <> 'Completed' AND DATE '2026-09-23' > t.due_date THEN 'Overdue'
            WHEN t.status = 'Blocked' THEN 'Blocked'
            ELSE 'On track'
        END AS schedule_health
    FROM tasks t
)
SELECT
    p.initials,
    th.task_id,
    th.task_name,
    th.status,
    th.schedule_health,
    th.due_date
FROM task_health th
JOIN participants p
    ON p.participant_id = th.participant_id
ORDER BY
    CASE th.schedule_health
        WHEN 'Overdue' THEN 1
        WHEN 'Blocked' THEN 2
        WHEN 'Completed late' THEN 3
        WHEN 'On track' THEN 4
        ELSE 5
    END,
    th.due_date;

-- ----------------------------------------------------------------
-- 8. Participant workload summary
-- ----------------------------------------------------------------
SELECT
    p.initials,
    COUNT(t.task_id) AS total_tasks,
    COUNT(t.task_id) FILTER (WHERE t.status = 'Completed') AS completed_tasks,
    COUNT(t.task_id) FILTER (WHERE t.status = 'In Progress') AS in_progress_tasks,
    COUNT(t.task_id) FILTER (WHERE t.status = 'Blocked') AS blocked_tasks,
    SUM(t.estimated_hours) AS estimated_hours,
    SUM(COALESCE(t.actual_hours, 0)) AS actual_hours,
    ROUND(AVG(t.completion_pct) * 100, 1) AS average_completion_pct
FROM participants p
LEFT JOIN tasks t
    ON t.participant_id = p.participant_id
GROUP BY p.participant_id, p.initials
ORDER BY p.initials;

-- ----------------------------------------------------------------
-- 9. Window functions
-- ----------------------------------------------------------------
SELECT
    p.initials,
    t.task_id,
    t.task_name,
    t.estimated_hours,
    SUM(t.estimated_hours) OVER (
        PARTITION BY p.participant_id
        ORDER BY t.task_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_estimated_hours,
    ROW_NUMBER() OVER (
        PARTITION BY p.participant_id
        ORDER BY t.due_date, t.task_id
    ) AS owner_task_sequence
FROM tasks t
JOIN participants p
    ON p.participant_id = t.participant_id
ORDER BY p.initials, owner_task_sequence;

WITH owner_progress AS (
    SELECT
        p.initials,
        AVG(t.completion_pct) AS average_completion,
        RANK() OVER (ORDER BY AVG(t.completion_pct) DESC) AS completion_rank
    FROM tasks t
    JOIN participants p
        ON p.participant_id = t.participant_id
    GROUP BY p.initials
)
SELECT
    initials,
    ROUND(average_completion * 100, 1) AS average_completion_pct,
    completion_rank
FROM owner_progress
ORDER BY completion_rank, initials;

-- ----------------------------------------------------------------
-- 10. Project performance summary
-- ----------------------------------------------------------------
SELECT
    pr.project_name,
    COUNT(t.task_id) AS total_tasks,
    COUNT(t.task_id) FILTER (WHERE t.status = 'Completed') AS completed_tasks,
    ROUND(
        100.0 * COUNT(t.task_id) FILTER (WHERE t.status = 'Completed')
        / NULLIF(COUNT(t.task_id), 0),
        1
    ) AS completion_rate_pct,
    SUM(t.estimated_hours) AS estimated_hours,
    SUM(COALESCE(t.actual_hours, 0)) AS actual_hours,
    SUM(COALESCE(t.actual_hours, 0)) - SUM(t.estimated_hours) AS variance_hours
FROM projects pr
LEFT JOIN tasks t
    ON t.project_id = pr.project_id
GROUP BY pr.project_id, pr.project_name
ORDER BY completion_rate_pct DESC, pr.project_name;

-- ----------------------------------------------------------------
-- 11. Data quality checks
-- ----------------------------------------------------------------
SELECT task_id, task_name
FROM tasks
WHERE status = 'Completed'
  AND completed_date IS NULL;

SELECT task_id, task_name
FROM tasks
WHERE actual_hours IS NOT NULL
  AND actual_hours > estimated_hours * 2;

SELECT
    task_name,
    participant_id,
    COUNT(*) AS duplicate_count
FROM tasks
GROUP BY task_name, participant_id
HAVING COUNT(*) > 1;

-- ----------------------------------------------------------------
-- 12. Comments and latest activity
-- ----------------------------------------------------------------
WITH latest_comment AS (
    SELECT
        tc.*,
        ROW_NUMBER() OVER (
            PARTITION BY tc.task_id
            ORDER BY tc.created_at DESC, tc.comment_id DESC
        ) AS row_num
    FROM task_comments tc
)
SELECT
    t.task_id,
    t.task_name,
    p.initials AS comment_author,
    lc.comment_text,
    lc.created_at
FROM tasks t
LEFT JOIN latest_comment lc
    ON lc.task_id = t.task_id
   AND lc.row_num = 1
LEFT JOIN participants p
    ON p.participant_id = lc.participant_id
ORDER BY t.task_id;

-- ----------------------------------------------------------------
-- 13. Transaction example for workshop practice
-- Run the statements separately and choose COMMIT or ROLLBACK.
-- ----------------------------------------------------------------
BEGIN;

UPDATE tasks
SET
    status = 'In Progress',
    completion_pct = 0.10,
    notes = 'Status changed during the GitHub Desktop workshop.'
WHERE task_id = 103
  AND status = 'Not Started';

SELECT task_id, task_name, status, completion_pct, notes
FROM tasks
WHERE task_id = 103;

ROLLBACK;

-- ----------------------------------------------------------------
-- 14. Reusable view
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_task_progress AS
SELECT
    t.task_id,
    p.initials AS owner,
    pr.project_name,
    t.task_name,
    t.category,
    t.priority,
    t.status,
    t.start_date,
    t.due_date,
    t.completed_date,
    t.estimated_hours,
    t.actual_hours,
    COALESCE(t.actual_hours, 0) - t.estimated_hours AS variance_hours,
    t.completion_pct,
    CASE
        WHEN t.completed_date IS NOT NULL AND t.completed_date <= t.due_date THEN 1
        WHEN t.completed_date IS NOT NULL AND t.completed_date > t.due_date THEN 0
        WHEN DATE '2026-09-23' <= t.due_date THEN 1
        ELSE 0
    END AS on_time_flag
FROM tasks t
JOIN participants p
    ON p.participant_id = t.participant_id
JOIN projects pr
    ON pr.project_id = t.project_id;

SELECT *
FROM vw_task_progress
ORDER BY owner, task_id;

-- ----------------------------------------------------------------
-- 15. Helpful indexes
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_tasks_participant
    ON tasks (participant_id);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status
    ON tasks (project_id, status);

CREATE INDEX IF NOT EXISTS idx_tasks_due_date
    ON tasks (due_date);

-- End of workshop script.
