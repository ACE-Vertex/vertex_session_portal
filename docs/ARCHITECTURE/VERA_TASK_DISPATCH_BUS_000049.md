# Vera Task Dispatch Bus 000049

One Vera may emit a strict task envelope for up to the other four Vera sessions.

[VERTEX_TASK_DISPATCH/1]
{
  "schema":"vertex-task-dispatch/1",
  "dispatch_id":"vertex-os-000001-from-vera02",
  "source_session":"vera-02",
  "targets":{"vera-01":"Task 1","vera-03":"Task 3","vera-04":"Task 4","vera-05":"Task 5"}
}
[/VERTEX_TASK_DISPATCH/1]

Human clicks TASK in the source pane. Only then is the marked block read, validated, confirmed, and sent. No background response scraping. No self-dispatch. Max four targets.
