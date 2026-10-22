"""Stable editorial seed data, independent from mock guidance/code fixtures."""
import re

from app.verified_problem_specs import VERIFIED_PROBLEM_SPECS
from app.catalog_40_facts import NEW_FACTS
from app.catalog_expansion_40 import NEW_EDITORIAL


def approach(key, name, pattern, summary, primary, order, quote, signals, thinking):
    return {
        "id": key,
        "name": name,
        "pattern": pattern,
        "summary": summary,
        "isPrimary": primary,
        "displayOrder": order,
        "thinkingSteps": thinking,
        "recognitionSignals": {"quote": quote, "bullets": signals},
    }


def problem(slug, *approaches):
    return {"slug": slug, "approaches": list(approaches)}


def related(slug, title, difficulty, reason):
    return {"slug": slug, "title": title, "difficulty": difficulty, "reason": reason}


def method_templates(python_signature, java_signature, javascript_signature, cpp_signature):
    """Curated LeetCode-style shells; these are not progressive Starter Code."""
    return {
        "python": f"class Solution:\n    def {python_signature}:\n        pass",
        "java": f"class Solution {{\n    public {java_signature} {{\n\n    }}\n}}",
        "javascript": f"var {javascript_signature} {{\n\n}};",
        "cpp": f"class Solution {{\npublic:\n    {cpp_signature} {{\n\n    }}\n}};",
    }


CURATED_PROBLEMS = {
    "two-sum": problem(
        "two-sum",
        approach("brute-force", "Brute Force", "Nested Loops",
                 "Compare every possible pair until the target sum is found.", False, 1,
                 "two numbers", ["The problem asks you to find a pair.",
                 "Trying every possible pair is a simple starting point when you do not yet see a shortcut."],
                 ["Consider every possible pair of indices.", "Check whether each pair reaches the target.",
                  "Recognize that this requires quadratic time."]),
        approach("hash-map", "One-pass Hash Map", "Hash Map",
                 "Remember previously visited values so complements can be found quickly.", True, 2,
                 "two numbers such that they add up to target",
                 ["For each number x, the other number you need is target - x.",
                  "Repeatedly asking whether a value appeared before is a clue to consider a Hash Map.",
                  "The answer needs indices, so remembering where each value appeared is useful."],
                 ["For each value, determine the complement needed to reach the target.",
                  "Check whether that complement has already been seen.",
                  "Store the current value for later lookups."]),
    ),
    "contains-duplicate": problem(
        "contains-duplicate",
        approach("brute-force", "Compare Every Pair", "Nested Loops",
                 "Compare each value with every later value.", False, 1, "appears at least twice",
                 ["The task only asks whether any two values match.",
                  "Trying every pair is the most direct baseline."],
                 ["Choose one value.", "Compare it with every value after it.",
                  "Stop as soon as a match is found."]),
        approach("hash-set", "Seen Values Set", "Hash Set",
                 "Remember values already visited and detect the first repeat.", True, 2,
                 "appears at least twice", ["You need to know whether a value appeared earlier.",
                  "A Set answers that yes-or-no question without storing positions."],
                 ["Scan the numbers once.", "Check whether the current value is already stored.",
                  "Store each new value for later checks."]),
    ),
    "valid-anagram": problem(
        "valid-anagram",
        approach("sorting", "Sort and Compare", "Sorting",
                 "Sort both strings so equal character collections line up.", False, 1, "t is an anagram of s",
                 ["Anagrams contain the same characters in a different order.",
                  "Sorting removes the importance of the original order."],
                 ["Reject strings with different lengths.", "Sort both strings.",
                  "Compare the sorted results."]),
        approach("frequency-count", "Character Frequency Count", "Frequency Map",
                 "Count each character and verify the counts balance.", True, 2, "t is an anagram of s",
                 ["The word “exactly” points to comparing character counts.",
                  "The positions do not matter, but the number of each character does."],
                 ["Count characters in the first string.", "Subtract counts using the second string.",
                  "Verify no count is left over."]),
    ),
    "group-anagrams": problem(
        "group-anagrams",
        approach("sorted-key", "Sorted String Key", "Hash Map + Sorting",
                 "Use each word's sorted characters as its group key.", False, 1, "group the anagrams together",
                 ["Words belong together when rearranging their letters makes them equal.",
                  "A shared normalized form can act as a group label."],
                 ["Transform each word into a sorted key.", "Append the word to that key's group.",
                  "Return all collected groups."]),
        approach("frequency-signature", "Character Count Signature", "Hash Map + Frequency Count",
                 "Use an immutable character-count signature as each anagram group's key.", True, 2,
                 "group the anagrams together", ["Anagrams have identical letter counts.",
                  "Many words need to be assigned to buckets by the same rule."],
                 ["Count the letters in each word.", "Turn the counts into a stable key.",
                  "Collect words that share the key."]),
    ),
    "valid-palindrome": problem(
        "valid-palindrome",
        approach("clean-and-reverse", "Clean and Reverse", "String Normalization",
                 "Normalize the text, reverse it, and compare both versions.", False, 1,
                 "reads the same forward and backward", ["Only letters and numbers matter after case is ignored.",
                  "The definition directly suggests comparing a string with its reverse."],
                 ["Build a lowercase alphanumeric string.", "Reverse the cleaned string.",
                  "Compare the two strings."]),
        approach("two-pointers", "Two Pointers", "Two Pointers",
                 "Move inward from both ends while skipping characters that do not count.", True, 2,
                 "reads the same forward and backward", ["Characters at matching distances from both ends must agree.",
                  "The input can be checked from both ends without building another string."],
                 ["Place one pointer at each end.", "Skip non-alphanumeric characters.",
                  "Compare valid characters and move inward."]),
    ),
    "two-sum-ii-input-array-is-sorted": problem(
        "two-sum-ii-input-array-is-sorted",
        approach("binary-search-complement", "Binary Search Each Complement", "Binary Search",
                 "For each number, binary-search the remaining sorted range for its complement.", False, 1,
                 "sorted in non-decreasing order", ["The needed partner is still target - x.",
                  "The sorted input makes binary search available."],
                 ["Choose a left value.", "Compute its needed partner.",
                  "Search only the later sorted values."]),
        approach("two-pointers", "Two Pointers", "Two Pointers",
                 "Move two ends inward according to whether their sum is too small or too large.", True, 2,
                 "sorted in non-decreasing order", ["The order tells you how to make a sum larger or smaller.",
                  "The answer is a pair, so pointers at both ends can narrow the search."],
                 ["Start at the smallest and largest values.", "Compare their sum with the target.",
                  "Move the side that can correct the sum."]),
    ),
    "3sum": problem(
        "3sum",
        approach("brute-force", "Try Every Triplet", "Nested Loops",
                 "Check every group of three indices and keep unique zero-sum triplets.", False, 1,
                 "return all the triplets", ["The problem asks for groups of exactly three values.",
                  "Trying every triplet establishes a straightforward baseline."],
                 ["Choose three distinct indices.", "Check whether their values total zero.",
                  "Avoid returning the same value triplet twice."]),
        approach("sort-and-two-pointers", "Sort with Two Pointers", "Sorting + Two Pointers",
                 "Fix one sorted value and find the remaining pair with two pointers.", True, 2,
                 "must not contain duplicate triplets", ["Fixing one value turns the task into a two-number sum.",
                  "Sorting helps move toward the target and skip duplicate triplets."],
                 ["Sort the values and fix one position.", "Search the remaining range from both ends.",
                  "Move pointers by the sum and skip duplicates."]),
    ),
    "best-time-to-buy-and-sell-stock": problem(
        "best-time-to-buy-and-sell-stock",
        approach("brute-force", "Try Every Buy and Sell Day", "Nested Loops",
                 "Compare every earlier buy day with every later sell day.", False, 1,
                 "choosing a single day to buy one stock",
                 ["The answer depends on an ordered pair of days.",
                  "Trying every valid buy-before-sell pair is a direct baseline."],
                 ["Choose each possible buy day.", "Check every later sell day.",
                  "Keep the largest positive difference."]),
        approach("running-minimum", "Running Minimum Price", "One-pass Tracking",
                 "Track the cheapest earlier price and the best profit available today.", True, 2,
                 "a different day in the future", ["A sale can only use a price seen earlier as its buy price.",
                  "For each day, only the cheapest earlier price matters."],
                 ["Remember the lowest price seen so far.", "Treat today's price as a possible sale.",
                  "Update the best profit and the running minimum."]),
    ),
    "longest-substring-without-repeating-characters": problem(
        "longest-substring-without-repeating-characters",
        approach("brute-force-substrings", "Check Every Substring", "Brute Force",
                 "Generate candidate substrings and test whether each one contains only unique characters.", False, 1,
                 "longest substring", ["A substring is a continuous piece of the text, with a start and an end.",
                  "Checking all possible pieces is a straightforward baseline."],
                 ["Consider every start and end position.", "Check each substring for repeated characters.",
                  "Track the longest valid length."]),
        approach("sliding-window-set", "Sliding Window with Set", "Sliding Window",
                 "Maintain a moving window of unique characters and shrink it when a duplicate appears.", True, 2,
                 "without duplicate characters", ["The answer is one continuous piece of text.",
                  "A repeated character is what makes the current piece invalid.",
                  "A Set can track which characters are in that piece."],
                 ["Keep a window with no duplicates.", "Expand its right side while possible.",
                  "Move the left side until a duplicate is removed."]),
        approach("sliding-window-index-map", "Sliding Window with Last Seen Index", "Sliding Window + Hash Map",
                 "Jump the left boundary past repeated characters using their most recent positions.", False, 3,
                 "without duplicate characters", ["A repeated character limits how far back a valid piece can start.",
                  "Knowing where it last appeared lets you skip directly forward."],
                 ["Store each character's latest index.", "Jump left past a repeat inside the window.",
                  "Update the best length and latest index."]),
    ),
    "longest-repeating-character-replacement": problem(
        "longest-repeating-character-replacement",
        approach("brute-force-windows", "Check Every Window", "Brute Force",
                 "Test every substring by counting how many replacements it needs.", False, 1,
                 "at most k times", ["The answer is a continuous substring.",
                  "Any chosen window is valid if only a small number of its characters must change."],
                 ["Choose every substring.", "Find its most common character.",
                  "Compare required replacements with k."]),
        approach("sliding-window-frequency", "Sliding Window with Frequencies", "Sliding Window",
                 "Keep the largest window whose non-majority characters can all be replaced.", True, 2,
                 "longest substring containing the same letter", ["The answer is a longest continuous range.",
                  "Within a range, every character except the most common one would need replacement."],
                 ["Expand a window and count its characters.", "Measure window size minus its largest count.",
                  "Shrink when that replacement count exceeds k."]),
    ),
    "valid-parentheses": problem(
        "valid-parentheses",
        approach("replace-pairs", "Repeated Pair Removal", "String Reduction",
                 "Repeatedly remove valid adjacent bracket pairs until no more can be removed.", False, 1,
                 "determine if the input string is valid", ["Even a nested group has a small matching pair inside it.",
                  "This suggests simplifying the string a pair at a time."],
                 ["Find adjacent valid bracket pairs.", "Remove them until the string stops changing.",
                  "Check whether anything remains."]),
        approach("stack", "Stack of Opening Brackets", "Stack",
                 "Track opening brackets so each closer matches the most recent unresolved opener.", True, 2,
                 "Open brackets must be closed in the correct order.", ["The order matters, so counts alone are not enough.",
                  "The last bracket opened must close first, which points to a Stack."],
                 ["Store each opening bracket.", "Match a closer with the latest opener.",
                  "Verify the stack is empty at the end."]),
    ),
    "min-stack": problem(
        "min-stack",
        approach("scan-for-minimum", "Scan for the Minimum (Teaching-Only Baseline)", "Stack + Linear Scan",
                 "Teaching-only baseline: scanning for the minimum does not meet the required O(1) getMin time and is not a submission-compliant solution.", False, 1,
                 "retrieving the minimum element", ["A regular stack already handles push, pop, and top.",
                  "Scanning all stored values is a simple baseline for minimum."],
                 ["Keep a normal stack.", "Use normal stack operations.",
                  "Scan every value when getMin is called."]),
        approach("paired-minimums", "Store Value and Current Minimum", "Augmented Stack",
                 "Store the minimum-so-far beside every pushed value.", True, 2,
                 "constant time", ["The minimum must be ready immediately, even after a pop.",
                  "Each stack level can remember the minimum that was valid at that moment."],
                 ["Pair each value with the current minimum.", "Restore the earlier minimum automatically on pop.",
                  "Read the top pair for both top and getMin."]),
    ),
    "daily-temperatures": problem(
        "daily-temperatures",
        approach("forward-scan", "Scan Future Days", "Nested Loops",
                 "For each day, scan forward until a warmer temperature appears.", False, 1,
                 "number of days you have to wait", ["Each answer asks about a later position.",
                  "Looking forward from every day is the direct baseline."],
                 ["Start from each day.", "Move forward until a warmer day appears.",
                  "Record the distance or zero."]),
        approach("monotonic-stack", "Monotonic Stack of Days", "Monotonic Stack",
                 "Keep unresolved days in decreasing temperature order until a warmer day resolves them.", True, 2,
                 "a warmer temperature", ["A new warm day may answer several earlier days at once.",
                  "Only days still waiting for something warmer need to be remembered."],
                 ["Store indices of unresolved days.", "Resolve colder days when a warmer value arrives.",
                  "Use index differences as waiting times."]),
    ),
    "binary-search": problem(
        "binary-search",
        approach("linear-scan", "Linear Scan (Teaching-Only Baseline)", "Array Traversal",
                 "Teaching-only baseline: checking values in order does not meet the required O(log n) time and is not a submission-compliant solution.", False, 1,
                 "sorted in ascending order", ["A scan works even without using the sorted order.",
                  "It is a useful correctness baseline."],
                 ["Visit each index.", "Compare its value with target.", "Return the matching index or -1."]),
        approach("binary-search", "Binary Search", "Binary Search",
                 "Repeatedly discard the half that cannot contain the target.", True, 2,
                 "sorted in ascending order", ["Sorted order tells you which side cannot contain the target.",
                  "The requested logarithmic time points directly to halving the search range."],
                 ["Track low and high bounds.", "Compare the middle value with target.",
                  "Keep only the possible half."]),
    ),
    "search-in-rotated-sorted-array": problem(
        "search-in-rotated-sorted-array",
        approach("linear-scan", "Linear Scan (Teaching-Only Baseline)", "Array Traversal",
                 "Teaching-only baseline: checking every value does not meet the required O(log n) time and is not a submission-compliant solution.", False, 1,
                 "return the index of target", ["A direct scan always finds a target if it exists.",
                  "It provides a baseline before using the array's structure."],
                 ["Visit each index.", "Compare with target.", "Return -1 if no value matches."]),
        approach("modified-binary-search", "Modified Binary Search", "Binary Search",
                 "Use the sorted half around each midpoint to decide where the target can remain.", True, 2,
                 "possibly rotated", ["After rotation, at least one side of any midpoint is still sorted.",
                  "The logarithmic requirement suggests preserving binary search's halving step."],
                 ["Find the midpoint and identify the sorted half.", "Check whether target falls inside that half.",
                  "Discard the impossible half."]),
    ),
    "reverse-linked-list": problem(
        "reverse-linked-list",
        approach("iterative-pointers", "Iterative Pointer Reversal", "Linked List Pointers",
                 "Reverse each next pointer while walking through the list once.", True, 1,
                 "reverse the list", ["Each node points only toward the next node.",
                  "Reversal means changing every arrow to point backward."],
                 ["Remember the previous and current nodes.", "Save the next node before changing a pointer.",
                  "Advance until the old tail becomes the new head."]),
        approach("recursive-unwind", "Recursive Unwind", "Recursion",
                 "Reverse the remaining list, then attach the current node behind it.", False, 2,
                 "reverse the list", ["A linked list naturally breaks into one node plus the rest.",
                  "If the rest is reversed, the current link can be flipped during the return steps."],
                 ["Recurse to the final node.", "Point the next node back to the current node.",
                  "Clear the old forward link."]),
    ),
    "merge-two-sorted-lists": problem(
        "merge-two-sorted-lists",
        approach("iterative-merge", "Iterative Merge", "Two Pointers",
                 "Repeatedly append the smaller current node from the two sorted lists.", True, 1,
                 "two sorted linked lists", ["Only the first remaining node of each list can be next.",
                  "This is the same choice used in the merge step of merge sort."],
                 ["Track one current node in each list.", "Append the smaller node and advance that list.",
                  "Attach whichever list remains."]),
        approach("recursive-merge", "Recursive Merge", "Recursion",
                 "Choose the smaller head and recursively merge everything after it.", False, 2,
                 "splicing together the nodes", ["The smaller head must come first in the merged result.",
                  "After choosing it, the remaining task has the same shape."],
                 ["Handle an empty list.", "Choose the smaller head.",
                  "Link it to the recursively merged remainder."]),
    ),
    "maximum-depth-of-binary-tree": problem(
        "maximum-depth-of-binary-tree",
        approach("depth-first-search", "Recursive Depth-First Search", "Tree DFS",
                 "Compute each subtree's depth and add the current level.", True, 1,
                 "maximum depth", ["Depth is one plus the deeper of the left and right subtrees.",
                  "A tree is naturally defined in terms of smaller subtrees."],
                 ["Return zero for an empty node.", "Compute both child depths.",
                  "Return one plus the larger result."]),
        approach("breadth-first-search", "Level-Order Traversal", "Tree BFS",
                 "Visit the tree one level at a time and count completed levels.", False, 2,
                 "number of nodes along the longest path", ["Tree depth can also be viewed as the number of levels.",
                  "A queue processes all nodes at one level together."],
                 ["Start a queue with the root.", "Process one complete level at a time.",
                  "Count levels until the queue is empty."]),
    ),
    "number-of-islands": problem(
        "number-of-islands",
        approach("depth-first-flood-fill", "Depth-First Flood Fill", "Grid DFS",
                 "Count each unvisited land cell as a new island and mark its connected land with DFS.", True, 1,
                 "surrounded by water and is formed by connecting adjacent lands",
                 ["An island is a connected group in a grid.",
                  "After finding one land cell, all connected land belongs to the same answer."],
                 ["Scan every grid cell.", "Start a count when unvisited land appears.",
                  "Mark all connected land with depth-first search."]),
        approach("breadth-first-flood-fill", "Breadth-First Flood Fill", "Grid BFS",
                 "Use a queue to mark every land cell connected to each newly found island.", False, 2,
                 "horizontally or vertically", ["Only four neighboring directions create a connection.",
                  "A queue can expand outward through one whole connected region."],
                 ["Start a queue at unvisited land.", "Visit valid land neighbors.",
                  "Continue until that island is fully marked."]),
    ),
    "climbing-stairs": problem(
        "climbing-stairs",
        approach("memoized-recursion", "Memoized Recursion", "Dynamic Programming",
                 "Cache the number of ways from each step so repeated subproblems are solved once.", False, 1,
                 "climb 1 or 2 steps", ["Every route starts with a one-step or two-step choice.",
                  "Those choices lead to the same smaller stair counts many times."],
                 ["Define ways for the remaining steps.", "Add the one-step and two-step cases.",
                  "Cache each result."]),
        approach("rolling-dynamic-programming", "Rolling Dynamic Programming", "Dynamic Programming",
                 "Build the answer from the previous two stair counts using constant space.", True, 2,
                 "distinct ways can you climb", ["The final move comes from one step below or two steps below.",
                  "Only the previous two counts are needed to compute the next count."],
                 ["Set base counts for the first small staircases.", "Add the previous two counts for each step.",
                  "Keep only the two most recent values."]),
    ),
}


CURATED_PROBLEMS.update({
    slug: problem(slug, *editorial["approaches"])
    for slug, editorial in NEW_EDITORIAL.items()
})


CURATED_PROBLEM_SPECS = {
    "two-sum": {
        "title": "Two Sum", "difficulty": "Easy",
        "summary": "Given an integer array and a target, return the indices of two distinct elements whose values add up to the target.",
        "submissionTemplates": method_templates(
            "twoSum(self, nums: list[int], target: int) -> list[int]",
            "int[] twoSum(int[] nums, int target)",
            "twoSum = function(nums, target)",
            "vector<int> twoSum(vector<int>& nums, int target)"),
    },
    "contains-duplicate": {
        "title": "Contains Duplicate", "difficulty": "Easy",
        "summary": "Given an integer array, return whether any value occurs at least twice.",
        "submissionTemplates": method_templates(
            "containsDuplicate(self, nums: list[int]) -> bool",
            "boolean containsDuplicate(int[] nums)",
            "containsDuplicate = function(nums)",
            "bool containsDuplicate(vector<int>& nums)"),
    },
    "valid-anagram": {
        "title": "Valid Anagram", "difficulty": "Easy",
        "summary": "Given two strings, return whether one can be formed by rearranging all characters of the other.",
        "submissionTemplates": method_templates(
            "isAnagram(self, s: str, t: str) -> bool",
            "boolean isAnagram(String s, String t)",
            "isAnagram = function(s, t)",
            "bool isAnagram(string s, string t)"),
    },
    "group-anagrams": {
        "title": "Group Anagrams", "difficulty": "Medium",
        "summary": "Given a list of strings, group together strings that are anagrams of one another.",
        "submissionTemplates": method_templates(
            "groupAnagrams(self, strs: list[str]) -> list[list[str]]",
            "List<List<String>> groupAnagrams(String[] strs)",
            "groupAnagrams = function(strs)",
            "vector<vector<string>> groupAnagrams(vector<string>& strs)"),
    },
    "valid-palindrome": {
        "title": "Valid Palindrome", "difficulty": "Easy",
        "summary": "Determine whether a string reads the same in both directions after ignoring non-alphanumeric characters and letter case.",
        "submissionTemplates": method_templates(
            "isPalindrome(self, s: str) -> bool",
            "boolean isPalindrome(String s)",
            "isPalindrome = function(s)",
            "bool isPalindrome(string s)"),
    },
    "two-sum-ii-input-array-is-sorted": {
        "title": "Two Sum II - Input Array Is Sorted", "difficulty": "Medium",
        "summary": "Given a non-decreasing integer array and a target, return the one-based indices of two distinct elements whose values add up to the target.",
        "submissionTemplates": method_templates(
            "twoSum(self, numbers: list[int], target: int) -> list[int]",
            "int[] twoSum(int[] numbers, int target)",
            "twoSum = function(numbers, target)",
            "vector<int> twoSum(vector<int>& numbers, int target)"),
    },
    "3sum": {
        "title": "3Sum", "difficulty": "Medium",
        "summary": "Given an integer array, return all unique value triplets whose sum is zero.",
        "submissionTemplates": method_templates(
            "threeSum(self, nums: list[int]) -> list[list[int]]",
            "List<List<Integer>> threeSum(int[] nums)",
            "threeSum = function(nums)",
            "vector<vector<int>> threeSum(vector<int>& nums)"),
    },
    "best-time-to-buy-and-sell-stock": {
        "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy",
        "summary": "Given daily stock prices, return the largest profit from one buy followed by one later sale, or zero if no profit is possible.",
        "submissionTemplates": method_templates(
            "maxProfit(self, prices: list[int]) -> int",
            "int maxProfit(int[] prices)",
            "maxProfit = function(prices)",
            "int maxProfit(vector<int>& prices)"),
    },
    "longest-substring-without-repeating-characters": {
        "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium",
        "summary": "Given a string, return the length of its longest contiguous substring containing no repeated characters.",
        "submissionTemplates": method_templates(
            "lengthOfLongestSubstring(self, s: str) -> int",
            "int lengthOfLongestSubstring(String s)",
            "lengthOfLongestSubstring = function(s)",
            "int lengthOfLongestSubstring(string s)"),
    },
    "longest-repeating-character-replacement": {
        "title": "Longest Repeating Character Replacement", "difficulty": "Medium",
        "summary": "Given an uppercase string and a replacement limit, return the maximum length of a substring that can be made of one repeated letter using at most that many replacements.",
        "submissionTemplates": method_templates(
            "characterReplacement(self, s: str, k: int) -> int",
            "int characterReplacement(String s, int k)",
            "characterReplacement = function(s, k)",
            "int characterReplacement(string s, int k)"),
    },
    "valid-parentheses": {
        "title": "Valid Parentheses", "difficulty": "Easy",
        "summary": "Determine whether a bracket string is correctly matched and nested.",
        "submissionTemplates": method_templates(
            "isValid(self, s: str) -> bool",
            "boolean isValid(String s)",
            "isValid = function(s)",
            "bool isValid(string s)"),
    },
    "min-stack": {
        "title": "Min Stack", "difficulty": "Medium",
        "summary": "Design a stack supporting push, pop, top, and retrieval of the current minimum element, with each operation running in constant time.",
        "submissionTemplates": {
            "python": "class MinStack:\n    def __init__(self):\n        pass\n\n    def push(self, value: int) -> None:\n        pass\n\n    def pop(self) -> None:\n        pass\n\n    def top(self) -> int:\n        pass\n\n    def getMin(self) -> int:\n        pass",
            "java": "class MinStack {\n    public MinStack() {\n\n    }\n\n    public void push(int value) {\n\n    }\n\n    public void pop() {\n\n    }\n\n    public int top() {\n\n    }\n\n    public int getMin() {\n\n    }\n}",
            "javascript": "var MinStack = function() {\n\n};\n\nMinStack.prototype.push = function(value) {\n\n};\n\nMinStack.prototype.pop = function() {\n\n};\n\nMinStack.prototype.top = function() {\n\n};\n\nMinStack.prototype.getMin = function() {\n\n};",
            "cpp": "class MinStack {\npublic:\n    MinStack() {\n\n    }\n\n    void push(int value) {\n\n    }\n\n    void pop() {\n\n    }\n\n    int top() {\n\n    }\n\n    int getMin() {\n\n    }\n};",
        },
    },
    "daily-temperatures": {
        "title": "Daily Temperatures", "difficulty": "Medium",
        "summary": "For each daily temperature, return how many days must pass before a warmer temperature occurs, using zero when none occurs.",
        "submissionTemplates": method_templates(
            "dailyTemperatures(self, temperatures: list[int]) -> list[int]",
            "int[] dailyTemperatures(int[] temperatures)",
            "dailyTemperatures = function(temperatures)",
            "vector<int> dailyTemperatures(vector<int>& temperatures)"),
    },
    "binary-search": {
        "title": "Binary Search", "difficulty": "Easy",
        "summary": "Given a sorted array of distinct integers and a target, return its index or -1 when it is absent.",
        "submissionTemplates": method_templates(
            "search(self, nums: list[int], target: int) -> int",
            "int search(int[] nums, int target)",
            "search = function(nums, target)",
            "int search(vector<int>& nums, int target)"),
    },
    "search-in-rotated-sorted-array": {
        "title": "Search in Rotated Sorted Array", "difficulty": "Medium",
        "summary": "Given a distinct ascending array that may have been rotated and a target, return the target index or -1 if absent.",
        "submissionTemplates": method_templates(
            "search(self, nums: list[int], target: int) -> int",
            "int search(int[] nums, int target)",
            "search = function(nums, target)",
            "int search(vector<int>& nums, int target)"),
    },
    "reverse-linked-list": {
        "title": "Reverse Linked List", "difficulty": "Easy",
        "summary": "Given the head of a singly linked list, reverse the list and return its new head.",
        "submissionTemplates": method_templates(
            "reverseList(self, head: ListNode | None) -> ListNode | None",
            "ListNode reverseList(ListNode head)",
            "reverseList = function(head)",
            "ListNode* reverseList(ListNode* head)"),
    },
    "merge-two-sorted-lists": {
        "title": "Merge Two Sorted Lists", "difficulty": "Easy",
        "summary": "Merge two non-decreasing singly linked lists by reusing their nodes and return the head of the merged sorted list.",
        "submissionTemplates": method_templates(
            "mergeTwoLists(self, list1: ListNode | None, list2: ListNode | None) -> ListNode | None",
            "ListNode mergeTwoLists(ListNode list1, ListNode list2)",
            "mergeTwoLists = function(list1, list2)",
            "ListNode* mergeTwoLists(ListNode* list1, ListNode* list2)"),
    },
    "maximum-depth-of-binary-tree": {
        "title": "Maximum Depth of Binary Tree", "difficulty": "Easy",
        "summary": "Given a binary tree root, return the number of nodes on the longest path from the root to a leaf.",
        "submissionTemplates": method_templates(
            "maxDepth(self, root: TreeNode | None) -> int",
            "int maxDepth(TreeNode root)",
            "maxDepth = function(root)",
            "int maxDepth(TreeNode* root)"),
    },
    "number-of-islands": {
        "title": "Number of Islands", "difficulty": "Medium",
        "summary": "Given a rectangular grid of land and water cells, return the number of separate land regions connected horizontally or vertically.",
        "submissionTemplates": method_templates(
            "numIslands(self, grid: List[List[str]]) -> int",
            "int numIslands(char[][] grid)",
            "numIslands = function(grid)",
            "int numIslands(vector<vector<char>>& grid)"),
    },
    "climbing-stairs": {
        "title": "Climbing Stairs", "difficulty": "Easy",
        "summary": "Given a staircase height, return the number of distinct ways to reach the top by taking one or two steps at a time.",
        "submissionTemplates": method_templates(
            "climbStairs(self, n: int) -> int",
            "int climbStairs(int n)",
            "climbStairs = function(n)",
            "int climbStairs(int n)"),
    },
}


CURATED_PROBLEM_SPECS.update({
    slug: {
        "title": facts["title"],
        "difficulty": facts["difficulty"],
        "summary": NEW_EDITORIAL[slug]["summary"],
        "submissionTemplates": facts["submissionTemplates"],
    }
    for slug, facts in NEW_FACTS.items()
})

if set(CURATED_PROBLEM_SPECS) != set(VERIFIED_PROBLEM_SPECS):
    raise ValueError("Every supported problem needs a source-audited specification.")
for _slug, _verified in VERIFIED_PROBLEM_SPECS.items():
    CURATED_PROBLEM_SPECS[_slug].update(_verified)


CURATED_RELATED_PROBLEMS = {
    "two-sum": {
        "easier": [related("running-sum-of-1d-array", "Running Sum of 1d Array", "Easy", "Warm up with array traversal and a running total.")],
        "similar": [related("contains-duplicate", "Contains Duplicate", "Easy", "Practice remembering values already seen.")],
        "harder": [related("3sum", "3Sum", "Medium", "Extend pair finding to unique triplets.")],
    },
    "contains-duplicate": {
        "easier": [],
        "similar": [related("valid-anagram", "Valid Anagram", "Easy", "Use counts or a set-like summary of values."),
                    related("two-sum", "Two Sum", "Easy", "Store earlier values for fast checks.")],
        "harder": [related("longest-substring-without-repeating-characters", "Longest Substring Without Repeating Characters", "Medium", "Track uniqueness inside a moving range.")],
    },
    "valid-anagram": {
        "easier": [related("contains-duplicate", "Contains Duplicate", "Easy", "Practice tracking repeated values first.")],
        "similar": [related("ransom-note", "Ransom Note", "Easy", "Compare available character counts."),
                    related("group-anagrams", "Group Anagrams", "Medium", "Use anagram signatures across many words.")],
        "harder": [],
    },
    "group-anagrams": {
        "easier": [related("valid-anagram", "Valid Anagram", "Easy", "First compare whether two words share a signature.")],
        "similar": [related("find-all-anagrams-in-a-string", "Find All Anagrams in a String", "Medium", "Recognize anagrams inside a moving window.")],
        "harder": [related("substring-with-concatenation-of-all-words", "Substring with Concatenation of All Words", "Hard", "Match grouped word counts inside substrings.")],
    },
    "valid-palindrome": {
        "easier": [],
        "similar": [related("reverse-string", "Reverse String", "Easy", "Practice inward-moving pointers."),
                    related("valid-palindrome-ii", "Valid Palindrome II", "Easy", "Allow one mismatch to be removed.")],
        "harder": [related("palindromic-substrings", "Palindromic Substrings", "Medium", "Count many palindromic ranges.")],
    },
    "two-sum-ii-input-array-is-sorted": {
        "easier": [related("binary-search", "Binary Search", "Easy", "Use sorted order to discard possibilities.")],
        "similar": [related("two-sum", "Two Sum", "Easy", "Solve the same pair goal without sorted input."),
                    related("squares-of-a-sorted-array", "Squares of a Sorted Array", "Easy", "Use two ends of a sorted array.")],
        "harder": [related("3sum", "3Sum", "Medium", "Fix one value and find a pair in sorted data.")],
    },
    "3sum": {
        "easier": [related("two-sum", "Two Sum", "Easy", "Master complement lookup for pairs."),
                   related("two-sum-ii-input-array-is-sorted", "Two Sum II - Input Array Is Sorted", "Medium", "Practice pair search with sorted two pointers.")],
        "similar": [related("3sum-closest", "3Sum Closest", "Medium", "Use the same sorted triplet search with a closest target.")],
        "harder": [related("4sum", "4Sum", "Medium", "Extend duplicate-aware sum search to four values.")],
    },
    "best-time-to-buy-and-sell-stock": {
        "easier": [related("running-sum-of-1d-array", "Running Sum of 1d Array", "Easy", "Practice maintaining one useful value during a scan.")],
        "similar": [related("best-time-to-buy-and-sell-stock-ii", "Best Time to Buy and Sell Stock II", "Medium", "Allow multiple transactions.")],
        "harder": [related("best-time-to-buy-and-sell-stock-with-cooldown", "Best Time to Buy and Sell Stock with Cooldown", "Medium", "Track more transaction states.")],
    },
    "longest-substring-without-repeating-characters": {
        "easier": [related("longest-continuous-increasing-subsequence", "Longest Continuous Increasing Subsequence", "Easy", "Track a contiguous run with a simpler rule.")],
        "similar": [related("maximum-sum-of-distinct-subarrays-with-length-k", "Maximum Sum of Distinct Subarrays With Length K", "Medium", "Maintain distinct values in a fixed window."),
                    related("longest-repeating-character-replacement", "Longest Repeating Character Replacement", "Medium", "Maintain a flexible valid window.")],
        "harder": [related("minimum-window-substring", "Minimum Window Substring", "Hard", "Manage character counts while shrinking a valid window.")],
    },
    "longest-repeating-character-replacement": {
        "easier": [related("longest-substring-without-repeating-characters", "Longest Substring Without Repeating Characters", "Medium", "Learn the basic variable sliding window.")],
        "similar": [related("max-consecutive-ones-iii", "Max Consecutive Ones III", "Medium", "Replace a limited number of values inside a window.")],
        "harder": [related("minimum-window-substring", "Minimum Window Substring", "Hard", "Track stricter character requirements while shrinking.")],
    },
    "valid-parentheses": {
        "easier": [related("maximum-nesting-depth-of-the-parentheses", "Maximum Nesting Depth of the Parentheses", "Easy", "Track one bracket type in valid input.")],
        "similar": [related("baseball-game", "Baseball Game", "Easy", "Use a stack for recent unresolved work."),
                    related("min-stack", "Min Stack", "Medium", "Augment a stack with extra state.")],
        "harder": [related("minimum-remove-to-make-valid-parentheses", "Minimum Remove to Make Valid Parentheses", "Medium", "Repair rather than only validate brackets.")],
    },
    "min-stack": {
        "easier": [related("valid-parentheses", "Valid Parentheses", "Easy", "Practice basic last-in-first-out behavior.")],
        "similar": [related("implement-queue-using-stacks", "Implement Queue using Stacks", "Easy", "Build a data structure from stacks.")],
        "harder": [related("maximum-frequency-stack", "Maximum Frequency Stack", "Hard", "Maintain richer metadata during stack operations.")],
    },
    "daily-temperatures": {
        "easier": [related("next-greater-element-i", "Next Greater Element I", "Easy", "Find the next larger value with a monotonic stack.")],
        "similar": [related("online-stock-span", "Online Stock Span", "Medium", "Resolve spans with a monotonic stack.")],
        "harder": [related("largest-rectangle-in-histogram", "Largest Rectangle in Histogram", "Hard", "Use monotonic boundaries for areas.")],
    },
    "binary-search": {
        "easier": [related("search-insert-position", "Search Insert Position", "Easy", "Return the boundary where a target belongs.")],
        "similar": [related("first-bad-version", "First Bad Version", "Easy", "Binary-search a yes-or-no boundary.")],
        "harder": [related("search-in-rotated-sorted-array", "Search in Rotated Sorted Array", "Medium", "Adapt binary search to a rotated order.")],
    },
    "search-in-rotated-sorted-array": {
        "easier": [related("binary-search", "Binary Search", "Easy", "Master the standard halving pattern first.")],
        "similar": [related("find-minimum-in-rotated-sorted-array", "Find Minimum in Rotated Sorted Array", "Medium", "Use the same rotated-order clues.")],
        "harder": [related("search-in-rotated-sorted-array-ii", "Search in Rotated Sorted Array II", "Medium", "Handle duplicates that obscure the sorted half.")],
    },
    "reverse-linked-list": {
        "easier": [related("middle-of-the-linked-list", "Middle of the Linked List", "Easy", "Practice moving pointers through a list.")],
        "similar": [related("merge-two-sorted-lists", "Merge Two Sorted Lists", "Easy", "Reconnect nodes while traversing lists."),
                    related("reverse-linked-list-ii", "Reverse Linked List II", "Medium", "Reverse only one list segment.")],
        "harder": [related("reverse-nodes-in-k-group", "Reverse Nodes in k-Group", "Hard", "Reverse repeated fixed-size list sections.")],
    },
    "merge-two-sorted-lists": {
        "easier": [related("reverse-linked-list", "Reverse Linked List", "Easy", "Practice safely rewiring list pointers.")],
        "similar": [related("merge-sorted-array", "Merge Sorted Array", "Easy", "Merge two sorted sequences in array form.")],
        "harder": [related("merge-k-sorted-lists", "Merge k Sorted Lists", "Hard", "Merge many sorted lists efficiently.")],
    },
    "maximum-depth-of-binary-tree": {
        "easier": [related("same-tree", "Same Tree", "Easy", "Practice recursive traversal of two subtrees.")],
        "similar": [related("minimum-depth-of-binary-tree", "Minimum Depth of Binary Tree", "Easy", "Find the nearest leaf instead of the farthest."),
                    related("balanced-binary-tree", "Balanced Binary Tree", "Easy", "Compare subtree depths while traversing.")],
        "harder": [related("binary-tree-maximum-path-sum", "Binary Tree Maximum Path Sum", "Hard", "Combine richer values from both subtrees.")],
    },
    "number-of-islands": {
        "easier": [related("flood-fill", "Flood Fill", "Easy", "Mark one connected grid region.")],
        "similar": [related("max-area-of-island", "Max Area of Island", "Medium", "Measure each connected land region."),
                    related("rotting-oranges", "Rotting Oranges", "Medium", "Expand through a grid in breadth-first layers.")],
        "harder": [related("making-a-large-island", "Making A Large Island", "Hard", "Reason about joining labeled regions.")],
    },
    "climbing-stairs": {
        "easier": [related("fibonacci-number", "Fibonacci Number", "Easy", "Practice the same previous-two recurrence.")],
        "similar": [related("min-cost-climbing-stairs", "Min Cost Climbing Stairs", "Easy", "Optimize a value over one-step and two-step moves."),
                    related("house-robber", "House Robber", "Medium", "Build a one-dimensional recurrence with two choices.")],
        "harder": [related("decode-ways", "Decode Ways", "Medium", "Count paths with more restrictive transitions.")],
    },
}


CURATED_RELATED_PROBLEMS.update({
    slug: {
        category: [
            related(other_slug, CURATED_PROBLEM_SPECS[other_slug]["title"],
                    CURATED_PROBLEM_SPECS[other_slug]["difficulty"], reason)
            for other_slug, reason in editorial["related"][category]
        ]
        for category in ("easier", "similar", "harder")
    }
    for slug, editorial in NEW_EDITORIAL.items()
})


def validate_curated_data(
    problems=CURATED_PROBLEMS,
    related_problems=CURATED_RELATED_PROBLEMS,
    problem_specs=CURATED_PROBLEM_SPECS,
):
    if set(problems) != set(related_problems) or set(problems) != set(problem_specs):
        raise ValueError("Every curated problem must have specification and related-problem data.")
    numbers = [spec["leetcodeNumber"] for spec in problem_specs.values()]
    if len(numbers) != len(set(numbers)) or any(not isinstance(number, int) or number <= 0 for number in numbers):
        raise ValueError("Curated problems need unique positive verified LeetCode numbers.")
    for slug, data in problems.items():
        spec = problem_specs[slug]
        if spec["difficulty"] not in {"Easy", "Medium", "Hard"}:
            raise ValueError(f"Problem '{slug}' has an invalid difficulty.")
        if not all(spec[field].strip() for field in ("title", "summary")):
            raise ValueError(f"Problem '{slug}' needs a title and factual summary.")
        if not spec["description"].strip() or spec["descriptionSourceType"] != "curated_restatement":
            raise ValueError(f"Problem '{slug}' needs a verified original restatement.")
        if spec["descriptionSourceUrl"] != f"https://leetcode.com/problems/{slug}/":
            raise ValueError(f"Problem '{slug}' needs its canonical official source URL.")
        if not spec["descriptionVerifiedAt"]:
            raise ValueError(f"Problem '{slug}' needs a source verification timestamp.")
        for limit in ("timeLimitMs", "memoryLimitMb"):
            value = spec[limit]
            if value is not None and (not isinstance(value, int) or value <= 0):
                raise ValueError(f"Problem '{slug}' has an invalid execution limit.")
        if not spec["constraints"] or not all(text.strip() for text in spec["constraints"]):
            raise ValueError(f"Problem '{slug}' needs ordered constraints.")
        if not spec["examples"] or any(
            not item["input"].strip() or not item["output"].strip() for item in spec["examples"]
        ):
            raise ValueError(f"Problem '{slug}' needs structured examples.")
        template_languages = set(spec["submissionTemplates"])
        if not template_languages or not template_languages <= {"python", "java", "javascript", "cpp"}:
            raise ValueError(f"Problem '{slug}' has invalid submission-template languages.")
        if not all(code.strip() for code in spec["submissionTemplates"].values()):
            raise ValueError(f"Problem '{slug}' has an empty submission template.")
        if data["slug"] != slug or not 1 <= len(data["approaches"]) <= 3:
            raise ValueError(f"Problem '{slug}' has invalid identity or approach count.")
        keys = [item["id"] for item in data["approaches"]]
        if len(keys) != len(set(keys)) or sum(item["isPrimary"] for item in data["approaches"]) != 1:
            raise ValueError(f"Problem '{slug}' needs unique keys and exactly one primary approach.")
        if any(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) is None for key in keys):
            raise ValueError(f"Problem '{slug}' has a non-kebab-case approach key.")
        if [item["displayOrder"] for item in data["approaches"]] != list(range(1, len(keys) + 1)):
            raise ValueError(f"Problem '{slug}' needs contiguous approach display order.")
        for item in data["approaches"]:
            signals = item["recognitionSignals"]["bullets"]
            if len(signals) not in (2, 3) or not all(text.strip() for text in signals):
                raise ValueError(f"Approach '{slug}/{item['id']}' needs two or three recognition signals.")
        seen = set()
        for category in ("easier", "similar", "harder"):
            for card in related_problems[slug].get(category, []):
                if card["slug"] == slug or card["slug"] in seen:
                    raise ValueError(f"Problem '{slug}' has a duplicate/self related card.")
                seen.add(card["slug"])


validate_curated_data()
