import os
import json
import re
import difflib

class TodoList:
    """
    Manages a JSON-backed to-do list with robust text matching, 
    fuzzy search capabilities, and automatic index maintenance.
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
        print("[System] Initializing Task Management (Todo List - JSON)...")
        
        self.file_path = os.path.join("data", "todo.json")
        os.makedirs("data", exist_ok=True)

        if not os.path.exists(self.file_path):
            self._save_data({"tasks": {}, "next_id": 1})

        print("[System] Todo List initialized successfully.")

    def _strip_fluff(self, text, phrases):
        """Removes conversational filler from the edges of the command payload."""
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
        Resolves a text payload to a specific task ID using sequential matching strategies:
        1. Exact match
        2. Substring match
        3. Unordered token subset match
        4. Fuzzy string matching
        """
        needle = needle.lower().strip()

        for tid, text in tasks.items():
            if text.lower().strip() == needle:
                return tid

        if len(needle) < 3:
            return None

        for tid, text in tasks.items():
            t = text.lower().strip()
            if needle in t or (len(t) >= 3 and t in needle):
                return tid

        needle_words = set(needle.split())
        for tid, text in tasks.items():
            task_words = set(text.lower().split())
            if needle_words.issubset(task_words):
                return tid

        lowered = {tid: text.lower().strip() for tid, text in tasks.items()}
        close = difflib.get_close_matches(needle, list(lowered.values()), n=1, cutoff=0.6)
        if close:
            for tid, text in lowered.items():
                if text == close[0]:
                    return tid

        return None

    def _load_data(self):
        """Safely loads list data, generating a clean state on corruption or missing file."""
        if not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0:
            return {"tasks": {}, "next_id": 1}
            
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"tasks": {}, "next_id": 1}

    def _save_data(self, data):
        """Serializes dictionary state to the JSON backing file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _reindex_tasks(self, data):
        """Reassigns sequential IDs to all tasks to prevent numbering gaps after deletions."""
        tasks = data.get("tasks", {})
        sorted_task_texts = [tasks[k] for k in sorted(tasks.keys(), key=int)]
        
        new_tasks = {str(index): text for index, text in enumerate(sorted_task_texts, start=1)}
        data["tasks"] = new_tasks
        data["next_id"] = len(new_tasks) + 1
        
        return data

    def handle_add(self, payload):
        """Appends a new task to the database."""
        task = self._strip_fluff(payload, self.ADD_FLUFF_PHRASES)

        if not task:
            return "What exactly would you like me to add?", "Failed to add task: No task provided."

        try:
            data = self._load_data()
            task_id = str(data["next_id"])

            data["tasks"][task_id] = task
            data["next_id"] += 1

            self._save_data(data)
            return f"I've added {task} to your list as task {task_id}.", f"Added task {task_id}: '{task}' to {self.file_path}."
        except Exception as e:
            return "I encountered an error saving your task.", f"JSON write error: {e}"

    def handle_read(self, payload):
        """Reads the entire task list, or a specific task if targeted by ID."""
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

        task_strings = [f"Task {tid}: {task}" for tid, task in tasks.items()]
        full_list = " ".join(task_strings)
        return f"You have {len(tasks)} tasks. {full_list}", "Read entire todo list successfully."

    def handle_clear(self, payload=""):
        """Removes tasks by ID or fuzzy name match, or clears the entire list."""
        original_payload = payload.strip().lower()
        
        if not original_payload:
            return "What would you like me to clear?", "Clear failed: No target provided."

        try:
            data = self._load_data()
            tasks = data.get("tasks", {})

            if not tasks:
                return "Your list is already empty.", "Todo list is empty."

            # Scenario 1: clear the complete list
            if original_payload in self.CLEAR_ALL_PHRASES:
                self._save_data({"tasks": {}, "next_id": 1})
                return "I have cleared all tasks from your to-do list.", "Successfully cleared all tasks and reset IDs."

            # Strip fluff only for specific task targeting to prevent self-defeating logic
            cleaned_payload = self._strip_fluff(payload, self.CLEAR_FLUFF_PHRASES)

            if not cleaned_payload:
                return "What would you like me to clear?", "Clear failed: No target provided after stripping."

            # Scenario 2: clear by task number
            number_match = self.TASK_NUMBER_PATTERN.match(cleaned_payload)
            if number_match:
                task_id = number_match.group(1)

                if task_id in tasks:
                    removed_task = tasks.pop(task_id)
                    data = self._reindex_tasks(data)
                    self._save_data(data)
                    return f"I have removed task {task_id}, which was: {removed_task}.", f"Removed task {task_id} by number."
                else:
                    return f"I couldn't find task number {task_id} on your list.", f"Clear failed: Task ID {task_id} not found."

            # Scenario 3: clear by task name
            found_id = self._find_task_by_name(cleaned_payload, tasks)
            if found_id:
                removed_task = tasks.pop(found_id)
                data = self._reindex_tasks(data)
                self._save_data(data)
                return f"I have removed {removed_task} from your list.", f"Removed task {found_id} by name matching '{cleaned_payload}'."
            else:
                return f"I couldn't find {cleaned_payload} on your list.", f"Clear failed: No task matching '{cleaned_payload}' found."

        except Exception as e:
            return "I encountered an error updating your list.", f"JSON clear error: {e}"
