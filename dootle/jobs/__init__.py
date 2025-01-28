"""
Doot/le Jobs.

Jobs are Tasks, which can create new Tasks as part of their action execution.
(Normally, Tasks can only depend on or require defined tasks, not create more).
This is achieved by returning a list of TaskSpec's from an action.

eg: A Job can walk a directory, and create a new task to handle each subdirectory found.

To assist this, this module provides a number of actions:
- Queue  : takes args[tasknames...], or a from_="..." to queue specified tasks
- Expand : takes a taskname, and creates new subtasks by applying args to it
- Match  : uses a mapping of {pattern -> taskname} to create a variety of new subtasks
- Shadow : take a path, and create a matching path with a different root
- Namer  : Names generated tasks
- Limit  : limits the number of generated subtasks


The order of operations you'll use here is:
1. {some sort of data generation}
2. Expand / Match
3. Shadow/Namer (maybe)
4. Limit (maybe)
5. Queue.



"""
