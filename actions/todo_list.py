import os
import json
import re
import difflib

class TodoList:
    """
    Task Management module using a structured JSON database. Supports
    adding a task, reading a single task or the whole list, and clearing
    a task by number, by name, or clearing the whole list.
    """

    ADD_FLUFF_PHRASES = [
        "to my todo list", "in my todo list", "on my todo list",
        "to the todo list", "in the todo list", "on the todo list",
        "to my list", "in my list", "on my list",
        "to the list", "in the list", "on the list",
        "to todo list", "in todo list", "on todo list",
        "todo list",
    ]

    CLEAR_FLUFF_PHRASES = [
        "from my todo list", "from the todo list",
        "off my todo list", "off the todo list",
        "on my todo list", "on the todo list",
        "from my list", "from the list",
        "off my list", "off the list",
        "on my list", "on the list",
        "from todo list", "off todo list", "on todo list",
    ]

    CLEAR_ALL_PHRASES = {
        "my list", "the list", "all", "everything",
        "todo list", "the todo list", "the complete todo list",
        "all my tasks", "all tasks", "all of my tasks", "all my todos",
        "everything on my list", "everything on the list",
        "the whole list", "my whole list", "whole list",
    }

    TASK_NUMBER_PATTERN = re.compile(
        r'^(?:the\s+)?(?:task|number|item|#)?\s*#?\s*(\d+)(?:st|nd|rd|th)?\s*(?:task|item)?\s*$',
        re.IGNORECASE
    )

    def __init__(self):
        """
        Initializes the Task Management module using a structured JSON database.
        """
        print("[System] Initializing Task Management (Todo List - JSON)...")

        # Safely point to the data directory
        self.file_path = os.path.join("data", "todo.json")

        # Ensure the 'data' directory exists
        os.makedirs("data", exist_ok=True)

        # If the file doesn't exist, create it with a blank dictionary structure
        if not os.path.exists(self.file_path):
            self._save_data({"tasks": {}, "next_id": 1})

        print("[System] Todo List initialized successfully.")

    # --- Text-handling helpers ---------------------------------------------

    def _strip_fluff(self, text, phrases):
        """
        Removes conversational filler phrases from the START or END of
        text only -- never the middle -- so a phrase like "todo list"
        can't accidentally eat part of a task's actual content just
        because it shows up mid-sentence. Runs multiple passes since more
        than one filler phrase can be stacked at an edge.
        """
        text = text.strip()
        changed = True
        while changed:
            changed = False
            lowered = text.lower()
            for fluff in phrases:
                if lowered.startswith(fluff):
                    text = text[len(fluff):].strip()
                    changed = True
                    break
                if lowered.endswith(fluff):
                    text = text[:len(text) - len(fluff)].strip()
                    changed = True
                    break
        return text

    def _find_task_by_name(self, needle, tasks):
        """
        Finds a single task matching the given text, trying progressively
        looser strategies until one succeeds:
          1. Exact match (case-insensitive)
          2. Substring match, either direction (guarded by a minimum
             length so a short word can't accidentally match an unrelated
             task by coincidence)
          3. Token-subset match -- every word the user said appears
             somewhere in the task, regardless of order (so "remove eggs
             and milk" matches a task stored as "buy milk and eggs")
          4. Fuzzy match, for minor typos or mis-transcribed words
        Returns the matching task id, or None if nothing matches with
        reasonable confidence.
        """
        needle = needle.lower().strip()

        # 1. Exact match -- always safe, regardless of length.
        for tid, text in tasks.items():
            if text.lower().strip() == needle:
                return tid

        # Looser matching is guarded behind a minimum length so a short,
        # ambiguous word can't latch onto an unrelated task by accident.
        if len(needle) < 3:
            return None

        # 2. Substring match, either direction.
        for tid, text in tasks.items():
            t = text.lower().strip()
            if needle in t or (len(t) >= 3 and t in needle):
                return tid

        # 3. Token-subset match (word order doesn't matter).
        needle_words = set(needle.split())
        for tid, text in tasks.items():
            task_words = set(text.lower().split())
            if needle_words.issubset(task_words):
                return tid

        # 4. Fuzzy fallback for minor typos / mis-heard words.
        lowered = {tid: text.lower().strip() for tid, text in tasks.items()}
        close = difflib.get_close_matches(needle, list(lowered.values()), n=1, cutoff=0.6)
        if close:
            for tid, text in lowered.items():
                if text == close[0]:
                    return tid

        return None

    # --- Storage helpers -----------------------------------------------------

    def _load_data(self):
        """Helper function to cleanly read the JSON file."""
        try:
            # Check if the file is completely empty (0 bytes) before trying to load it
            if os.path.getsize(self.file_path) == 0:
                return {"tasks": {}, "next_id": 1}

            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
            # If the file has corrupted data in it, automatically reset to a clean state
            return {"tasks": {}, "next_id": 1}

    def _save_data(self, data):
        """Helper function to safely save data back to the JSON file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _reindex_tasks(self, data):
        """
        Helper function to automatically shift numbers and reset next_id
        after a task is deleted, leaving no gaps in the numbering.
        """
        tasks = data.get("tasks", {})

        # Extract all tasks and sort them by their original integer IDs to keep order intact
        sorted_task_texts = [tasks[k] for k in sorted(tasks.keys(), key=int)]

        new_tasks = {}
        # Enumerate automatically starts counting from 1
        for index, text in enumerate(sorted_task_texts, start=1):
            new_tasks[str(index)] = text

        data["tasks"] = new_tasks
        data["next_id"] = len(new_tasks) + 1
        return data

    # --- Public actions --------------------------------------------------

    def handle_add(self, payload):
        """
        Adds a new task and assigns it a permanent task number.
        """
        task = self._strip_fluff(payload, self.ADD_FLUFF_PHRASES)

        if not task:
            return "What exactly would you like me to add?", "Failed to add task: No task provided."

        try:
            data = self._load_data()
            task_id = str(data["next_id"])  # Get the next available number

            # Save the task and increment the ID tracker
            data["tasks"][task_id] = task
            data["next_id"] += 1

            self._save_data(data)
            return f"I've added {task} to your list as task {task_id}.", f"Added task {task_id}: '{task}' to {self.file_path}."
        except Exception as e:
            return "I encountered an error saving your task.", f"JSON write error: {e}"

    def handle_read(self, payload):
        """
        Reads the whole list, or a specific task if the payload is
        specifically a task-number reference (e.g. "task 2", "#2").
        """
        data = self._load_data()
        tasks = data.get("tasks", {})

        if not tasks:
            return "Your to-do list is currently empty.", "Todo list is empty."

        number_match = self.TASK_NUMBER_PATTERN.match(payload.strip())

        if number_match:
            task_id = number_match.group(1)

            if task_id in tasks:
                specific_task = tasks[task_id]
                return f"Task {task_id} is: {specific_task}", f"Read task {task_id} successfully."
            else:
                return f"You don't have a task number {task_id} on your list.", f"Requested task {task_id} out of bounds."

        else:
            # No clean number reference, so read the whole list
            task_strings = [f"Task {tid}: {task}" for tid, task in tasks.items()]
            full_list = " ".join(task_strings)
            return f"You have {len(tasks)} tasks. {full_list}", "Read entire todo list successfully."

    def handle_clear(self, payload=""):
        """
        Intelligently clears the whole list, a specific task by number, or
        a specific task by name (with substring/word-order/fuzzy fallback
        matching), and re-indexes the remaining numbers automatically.
        """
        payload = self._strip_fluff(payload, self.CLEAR_FLUFF_PHRASES)

        if not payload:
            return "What would you like me to clear?", "Failed to clear: No target provided."

        try:
            data = self._load_data()
            tasks = data.get("tasks", {})

            if not tasks:
                return "Your list is already empty.", "Todo list is empty."

            # Scenario 1: clear the complete list
            if payload.lower() in self.CLEAR_ALL_PHRASES:
                self._save_data({"tasks": {}, "next_id": 1})
                return "I have cleared all tasks from your to-do list.", "Successfully cleared all tasks and reset IDs."

            # Scenario 2: clear by task number ("2", "task 2", "#2", "the 2nd task", ...)
            number_match = self.TASK_NUMBER_PATTERN.match(payload)
            if number_match:
                task_id = number_match.group(1)

                if task_id in tasks:
                    removed_task = tasks.pop(task_id)
                    # Instantly re-index and shift numbers down
                    data = self._reindex_tasks(data)
                    self._save_data(data)
                    return f"I have removed task {task_id}, which was: {removed_task}.", f"Removed task {task_id} by number."
                else:
                    return f"I couldn't find task number {task_id} on your list.", f"Clear failed: Task ID {task_id} not found."

            # Scenario 3: clear by task name
            found_id = self._find_task_by_name(payload, tasks)
            if found_id:
                removed_task = tasks.pop(found_id)
                # Instantly re-index and shift numbers down
                data = self._reindex_tasks(data)
                self._save_data(data)
                return f"I have removed {removed_task} from your list.", f"Removed task {found_id} by name matching '{payload}'."
            else:
                return f"I couldn't find {payload} on your list.", f"Clear failed: No task matching '{payload}' found."

        except Exception as e:
            return "I encountered an error updating your list.", f"JSON clear error: {e}"