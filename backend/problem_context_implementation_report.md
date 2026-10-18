# Verified problem context implementation

## Result and scope

The 20 supported problems now have original, approach-neutral task restatements, all examples and constraints shown on their public LeetCode pages at review time, an official source URL, and a fixed UTC verification timestamp. They remain in the existing exact-sync SQLite seed. Groq receives this DB context through the existing Hints, Starter Code, and Full Solution routes; public API payloads and generation prompts are unchanged. No live Groq request was made for this milestone.

Review timestamp: `2026-10-18T05:45:28+00:00`. Source type: `curated_restatement`, meaning the descriptions and example explanations are original prose based on the linked official pages, not verbatim LeetCode copy. Example inputs/outputs and numeric constraints are factual data. The URL in each row is also the persisted `description_source_url`.

## Twenty-page source audit

| # | Problem / official source | Examples in order | Constraints | Unresolved or qualified facts |
|---:|---|---:|---:|---|
| 1 | [Two Sum](https://leetcode.com/problems/two-sum/) | 3 | 4 | Faster than O(n²) is an optional follow-up. |
| 217 | [Contains Duplicate](https://leetcode.com/problems/contains-duplicate/) | 3 | 2 | None. |
| 242 | [Valid Anagram](https://leetcode.com/problems/valid-anagram/) | 2 | 2 | Unicode is an optional follow-up. |
| 49 | [Group Anagrams](https://leetcode.com/problems/group-anagrams/) | 3 | 3 | Group and member order may vary. |
| 125 | [Valid Palindrome](https://leetcode.com/problems/valid-palindrome/) | 3 | 2 | None. |
| 167 | [Two Sum II - Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/) | 3 | 5 | O(1) extra space is required, stored separately. |
| 15 | [3Sum](https://leetcode.com/problems/3sum/) | 3 | 2 | Triplet order may vary. |
| 121 | [Best Time to Buy and Sell Stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock/) | 2 | 2 | None. |
| 3 | [Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/) | 3 | 2 | None. |
| 424 | [Longest Repeating Character Replacement](https://leetcode.com/problems/longest-repeating-character-replacement/) | 2 | 3 | None. |
| 20 | [Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | 5 | 2 | Five examples appear on the current page. |
| 155 | [Min Stack](https://leetcode.com/problems/min-stack/) | 1 | 3 | O(1) per operation is required. |
| 739 | [Daily Temperatures](https://leetcode.com/problems/daily-temperatures/) | 3 | 2 | None. |
| 704 | [Binary Search](https://leetcode.com/problems/binary-search/) | 2 | 4 | O(log n) runtime is required. |
| 33 | [Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/) | 3 | 5 | O(log n) runtime is required. |
| 206 | [Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/) | 3 | 2 | None. |
| 21 | [Merge Two Sorted Lists](https://leetcode.com/problems/merge-two-sorted-lists/) | 3 | 3 | Existing nodes must be connected. |
| 104 | [Maximum Depth of Binary Tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/) | 2 | 2 | None. |
| 200 | [Number of Islands](https://leetcode.com/problems/number-of-islands/) | 2 | 4 | Grid values are the characters `"0"` and `"1"`. |
| 70 | [Climbing Stairs](https://leetcode.com/problems/climbing-stairs/) | 2 | 1 | None. |

Total: **53 examples and 55 constraints**. Official public pages did not establish a time limit in milliseconds or memory limit in megabytes for these problems; both fields remain `NULL` for all 20 rather than inventing values. “None” in the final column means no other unresolved fact was found during this audit, not that runtime limits were established.

Three retained alternate approaches cannot satisfy official mandatory complexity requirements: `min-stack/scan-for-minimum`, `binary-search/linear-scan`, and `search-in-rotated-sorted-array/linear-scan`. Their stable approach IDs were preserved and their summaries now explicitly identify them as noncompliant teaching baselines. The primary approach for each problem remains suitable for the required complexity. Full-solution generation for those three alternate IDs still needs a product decision if strict official compliance is expected; this data milestone does not change generation behavior. Existing language submission templates were retained, with no demonstrated signature error requiring a change.

## SQLite and context flow

Alembic revision `0003` adds nullable `Problem` columns: `leetcode_number` (unique when present), `description`, `description_source_url`, `description_source_type`, `description_verified_at`, `time_limit_ms`, `memory_limit_mb`, `time_complexity_instruction`, and `space_complexity_instruction`. Nullable columns keep older and unrelated problem rows valid. The source data lives in `app/verified_problem_specs.py`, merged by slug into `CURATED_PROBLEM_SPECS`; the established seed updates scalar fields and exact-syncs ordered examples, constraints, and existing child metadata without replacing retained row IDs.

Both context loaders use one serializer for the problem facts. Hints adds the selected canonical approach and no submission template. Starter Code and Full Solution add the selected approach and only the requested language's template. The current Groq provider still serializes that context using its existing code. No prompt, provider, validator, fallback, or public response shape was changed.

## Migration and verification

- Existing local SQLite database: backed up to ignored `backend/leetcoach.pre0003.db`, migrated from `0002` to `0003`, and reseeded. It contains 20 described problems, 41 approaches, 53 examples, and 55 constraints.
- Automated migration coverage: fresh database upgraded to head; `0003` downgraded/reapplied over existing rows; reseed preserved problem IDs and an unrelated row. Exact-sync tests cover repeat seed, content updates, stale-child removal, and retained IDs.
- `py -B -m alembic check`: no new upgrade operations detected.
- Backend: `py -B -m unittest discover -s tests -q` — **99 passed**. The evaluation harness used fake clients; no real Groq requests were sent.
- Frontend: `npm test -- --run` — **101 passed**. Build: `npm run build` — passed.
- `git diff --check` — passed.

## Actual serialized SQLite context samples

The following JSON was read back from the migrated, reseeded local SQLite database through the production context loaders. It was not copied from the seed dictionaries.

### Hints: Two Sum / hash-map (no submission template)

```json
{
  "problem": {
    "slug": "two-sum",
    "leetcodeNumber": 1,
    "title": "Two Sum",
    "difficulty": "Easy",
    "summary": "Given an integer array and a target, return the indices of two distinct elements whose values add up to the target.",
    "description": "Given an integer array nums and an integer target, return the zero-based indices of two different array elements whose values sum to target. Exactly one valid pair is guaranteed. An element cannot be chosen twice, even when its value is used twice; either order of the two indices is accepted.",
    "descriptionSourceUrl": "https://leetcode.com/problems/two-sum/",
    "descriptionSourceType": "curated_restatement",
    "descriptionVerifiedAt": "2026-10-18T05:45:28+00:00",
    "timeLimitMs": null,
    "memoryLimitMb": null,
    "timeComplexityInstruction": "Optional follow-up: find a method faster than O(n^2).",
    "spaceComplexityInstruction": null,
    "constraints": [
      "2 <= nums.length <= 10^4",
      "-10^9 <= nums[i] <= 10^9",
      "-10^9 <= target <= 10^9",
      "Exactly one valid pair exists."
    ],
    "examples": [
      {
        "input": "nums = [2,7,11,15], target = 9",
        "output": "[0,1]",
        "explanation": "The values at indices 0 and 1 sum to 9."
      },
      {
        "input": "nums = [3,2,4], target = 6",
        "output": "[1,2]",
        "explanation": null
      },
      {
        "input": "nums = [3,3], target = 6",
        "output": "[0,1]",
        "explanation": null
      }
    ]
  },
  "approach": {
    "id": "hash-map",
    "name": "One-pass Hash Map",
    "pattern": "Hash Map",
    "summary": "Remember previously visited values so complements can be found quickly.",
    "isPrimary": true,
    "displayOrder": 2,
    "thinkingSteps": [
      "For each value, determine the complement needed to reach the target.",
      "Check whether that complement has already been seen.",
      "Store the current value for later lookups."
    ],
    "recognitionSignals": {
      "bullets": [
        "For each number x, the other number you need is target - x.",
        "Repeatedly asking whether a value appeared before is a clue to consider a Hash Map.",
        "The answer needs indices, so remembering where each value appeared is useful."
      ],
      "quote": "two numbers such that they add up to target"
    }
  }
}
```

### Starter Code: Min Stack / paired-minimums / JavaScript

```json
{
  "problem": {
    "slug": "min-stack",
    "leetcodeNumber": 155,
    "title": "Min Stack",
    "difficulty": "Medium",
    "summary": "Design a stack supporting push, pop, top, and retrieval of the current minimum element, with each operation running in constant time.",
    "description": "Implement a MinStack object. Its constructor creates an empty stack; push(value) adds a value; pop() removes the top value; top() returns that value; and getMin() returns the smallest value currently stored. Each method must take constant time. Calls to pop, top, and getMin are guaranteed to occur only when the stack is nonempty. The example's operation and argument arrays are parallel, and constructor and void calls produce null results.",
    "descriptionSourceUrl": "https://leetcode.com/problems/min-stack/",
    "descriptionSourceType": "curated_restatement",
    "descriptionVerifiedAt": "2026-10-18T05:45:28+00:00",
    "timeLimitMs": null,
    "memoryLimitMb": null,
    "timeComplexityInstruction": "Required: every MinStack operation runs in O(1) time.",
    "spaceComplexityInstruction": null,
    "constraints": [
      "-2^31 <= value <= 2^31 - 1",
      "pop, top, and getMin are called only on nonempty stacks.",
      "At most 3 * 10^4 total calls are made to push, pop, top, and getMin."
    ],
    "examples": [
      {
        "input": "[\"MinStack\",\"push\",\"push\",\"push\",\"getMin\",\"pop\",\"top\",\"getMin\"]\n[[],[-2],[0],[-3],[],[],[],[]]",
        "output": "[null,null,null,null,-3,null,0,-2]",
        "explanation": "After pushing -2, 0, and -3, the minimum is -3. Popping -3 exposes top 0 and minimum -2."
      }
    ],
    "submissionTemplate": {
      "language": "javascript",
      "code": "var MinStack = function() {\n\n};\n\nMinStack.prototype.push = function(val) {\n\n};\n\nMinStack.prototype.pop = function() {\n\n};\n\nMinStack.prototype.top = function() {\n\n};\n\nMinStack.prototype.getMin = function() {\n\n};"
    }
  },
  "approach": {
    "id": "paired-minimums",
    "name": "Store Value and Current Minimum",
    "pattern": "Augmented Stack",
    "summary": "Store the minimum-so-far beside every pushed value.",
    "isPrimary": true,
    "displayOrder": 2,
    "thinkingSteps": [
      "Pair each value with the current minimum.",
      "Restore the earlier minimum automatically on pop.",
      "Read the top pair for both top and getMin."
    ],
    "recognitionSignals": {
      "bullets": [
        "The minimum must be ready immediately, even after a pop.",
        "Each stack level can remember the minimum that was valid at that moment."
      ],
      "quote": "constant time"
    }
  }
}
```

### Full Solution: Number of Islands / depth-first-flood-fill / Python

```json
{
  "problem": {
    "slug": "number-of-islands",
    "leetcodeNumber": 200,
    "title": "Number of Islands",
    "difficulty": "Medium",
    "summary": "Given a rectangular grid of land and water cells, return the number of separate land regions connected horizontally or vertically.",
    "description": "Given a nonempty rectangular grid of character '1' land cells and '0' water cells, return the number of connected land regions. Land connects only through shared horizontal or vertical edges, not diagonals. Treat the area beyond all four grid borders as water.",
    "descriptionSourceUrl": "https://leetcode.com/problems/number-of-islands/",
    "descriptionSourceType": "curated_restatement",
    "descriptionVerifiedAt": "2026-10-18T05:45:28+00:00",
    "timeLimitMs": null,
    "memoryLimitMb": null,
    "timeComplexityInstruction": null,
    "spaceComplexityInstruction": null,
    "constraints": [
      "m == grid.length",
      "n == grid[i].length",
      "1 <= m, n <= 300",
      "Every grid[i][j] is the character '0' or '1'."
    ],
    "examples": [
      {
        "input": "grid = [[\"1\",\"1\",\"1\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"1\",\"0\"],[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"0\",\"0\",\"0\",\"0\",\"0\"]]",
        "output": "1",
        "explanation": null
      },
      {
        "input": "grid = [[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"1\",\"1\",\"0\",\"0\",\"0\"],[\"0\",\"0\",\"1\",\"0\",\"0\"],[\"0\",\"0\",\"0\",\"1\",\"1\"]]",
        "output": "3",
        "explanation": null
      }
    ],
    "submissionTemplate": {
      "language": "python",
      "code": "class Solution:\n    def numIslands(self, grid: List[List[str]]) -> int:\n        pass"
    }
  },
  "approach": {
    "id": "depth-first-flood-fill",
    "name": "Depth-First Flood Fill",
    "pattern": "Grid DFS",
    "summary": "Count each unvisited land cell as a new island and mark its connected land with DFS.",
    "isPrimary": true,
    "displayOrder": 1,
    "thinkingSteps": [
      "Scan every grid cell.",
      "Start a count when unvisited land appears.",
      "Mark all connected land with depth-first search."
    ],
    "recognitionSignals": {
      "bullets": [
        "An island is a connected group in a grid.",
        "After finding one land cell, all connected land belongs to the same answer."
      ],
      "quote": "surrounded by water and is formed by connecting adjacent lands"
    }
  }
}
```

## Git status and suggested commit

At report completion, the task's new files are `backend/alembic/versions/0003_add_verified_problem_context.py`, `backend/app/verified_problem_specs.py`, and this report. Task edits are in `backend/app/models.py`, `backend/app/seed.py`, `backend/app/services/problem_repository.py`, `backend/app/stable_data.py`, `backend/tests/test_problem_specs.py`, and `backend/tests/test_seed_sync.py`. Three pre-existing evaluation-only edits remain untouched: `backend/evaluation/run_evaluation.py`, `backend/evaluation/validators.py`, and `backend/tests/test_evaluation_harness.py`. The SQLite database and its pre-migration backup are ignored by Git. Nothing was committed or pushed.

Suggested commit message for the context milestone: `Add verified SQLite problem context for all 20 seeded problems`.
