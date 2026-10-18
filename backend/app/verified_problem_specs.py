"""Source-audited, approach-neutral restatements of the 20 supported problems.

Descriptions and explanations are original editorial prose. Example inputs,
outputs, and numeric constraints are factual data checked against the linked
public LeetCode problem pages on 2026-10-18 (UTC). No page text is scraped at
runtime, and these descriptions are not presented as verbatim LeetCode copy.
"""

VERIFIED_AT = "2026-10-18T05:45:28+00:00"


def example(input_text, output_text, explanation=None):
    return {"input": input_text, "output": output_text, "explanation": explanation}


def verified(slug, number, description, constraints, examples,
             time_instruction=None, space_instruction=None):
    return {
        "leetcodeNumber": number,
        "description": description,
        "descriptionSourceUrl": f"https://leetcode.com/problems/{slug}/",
        "descriptionSourceType": "curated_restatement",
        "descriptionVerifiedAt": VERIFIED_AT,
        "timeLimitMs": None,
        "memoryLimitMb": None,
        "timeComplexityInstruction": time_instruction,
        "spaceComplexityInstruction": space_instruction,
        "constraints": constraints,
        "examples": examples,
    }


VERIFIED_PROBLEM_SPECS = {
    "two-sum": verified(
        "two-sum", 1,
        "Given an integer array nums and an integer target, return the zero-based indices of two different array elements whose values sum to target. Exactly one valid pair is guaranteed. An element cannot be chosen twice, even when its value is used twice; either order of the two indices is accepted.",
        ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9",
         "-10^9 <= target <= 10^9", "Exactly one valid pair exists."],
        [example("nums = [2,7,11,15], target = 9", "[0,1]", "The values at indices 0 and 1 sum to 9."),
         example("nums = [3,2,4], target = 6", "[1,2]"),
         example("nums = [3,3], target = 6", "[0,1]")],
        time_instruction="Optional follow-up: find a method faster than O(n^2)."),
    "contains-duplicate": verified(
        "contains-duplicate", 217,
        "Given an integer array nums, return true when some value occurs at two or more different positions. Return false when every array value is distinct.",
        ["1 <= nums.length <= 10^5", "-10^9 <= nums[i] <= 10^9"],
        [example("nums = [1,2,3,1]", "true", "The value 1 occurs at two positions."),
         example("nums = [1,2,3,4]", "false", "No value repeats."),
         example("nums = [1,1,1,3,3,4,3,2,4,2]", "true")]),
    "valid-anagram": verified(
        "valid-anagram", 242,
        "Given strings s and t, return true if t can be made by rearranging every character of s exactly once. Character counts must therefore match, regardless of order; otherwise return false. The required inputs contain lowercase English letters; Unicode is only an optional follow-up, not part of the required contract.",
        ["1 <= s.length, t.length <= 5 * 10^4",
         "s and t contain lowercase English letters only."],
        [example('s = "anagram", t = "nagaram"', "true"),
         example('s = "rat", t = "car"', "false")]),
    "group-anagrams": verified(
        "group-anagrams", 49,
        "Given an array of strings strs, partition its strings into groups so that strings belong to the same group exactly when their characters can be rearranged into one another. Include each input string once. The order of groups and the order of strings within a group are unrestricted; empty strings are valid inputs.",
        ["1 <= strs.length <= 10^4", "0 <= strs[i].length <= 100",
         "Each strs[i] contains lowercase English letters only."],
        [example('strs = ["eat","tea","tan","ate","nat","bat"]',
                 '[["bat"],["nat","tan"],["ate","eat","tea"]]',
                 "The six strings form three anagram groups; their ordering may vary."),
         example('strs = [""]', '[[""]]'),
         example('strs = ["a"]', '[["a"]')]),
    "valid-palindrome": verified(
        "valid-palindrome", 125,
        "Given a printable-ASCII string s, ignore characters that are not letters or digits and compare the remaining characters without regard to letter case. Return true if that normalized sequence reads the same in both directions; otherwise return false. A sequence with no retained characters is a palindrome.",
        ["1 <= s.length <= 2 * 10^5", "s contains printable ASCII characters only."],
        [example('s = "A man, a plan, a canal: Panama"', "true",
                 "After case folding and filtering, the characters read identically in both directions."),
         example('s = "race a car"', "false", "The filtered characters do not match in reverse order."),
         example('s = " "', "true", "Filtering leaves an empty sequence, which is valid.")]),
    "two-sum-ii-input-array-is-sorted": verified(
        "two-sum-ii-input-array-is-sorted", 167,
        "Given a non-decreasing integer array numbers and a target, find two different elements whose sum is target. Return their one-based positions as a two-element array in increasing index order. Exactly one answer is guaranteed, and the same array element cannot be used twice. Use only constant extra space.",
        ["2 <= numbers.length <= 3 * 10^4", "-1000 <= numbers[i] <= 1000",
         "numbers is sorted in non-decreasing order.", "-1000 <= target <= 1000",
         "Exactly one valid pair exists."],
        [example("numbers = [2,7,11,15], target = 9", "[1,2]", "The first two values sum to 9; positions start at 1."),
         example("numbers = [2,3,4], target = 6", "[1,3]", "Values 2 and 4 occupy one-based positions 1 and 3."),
         example("numbers = [-1,0], target = -1", "[1,2]", "The two values sum to -1.")],
        space_instruction="Required: use O(1) extra space."),
    "3sum": verified(
        "3sum", 15,
        "Given an integer array nums, return every distinct triplet of values that can be chosen from three different indices and whose sum is zero. Do not repeat a triplet in the result merely because different indices or orders produce the same values. The order of triplets and the order of values inside each triplet do not matter.",
        ["3 <= nums.length <= 3000", "-10^5 <= nums[i] <= 10^5"],
        [example("nums = [-1,0,1,2,-1,-4]", "[[-1,-1,2],[-1,0,1]]",
                 "Several index combinations yield zero, but only two distinct value triplets remain."),
         example("nums = [0,1,1]", "[]", "Its only possible triplet does not sum to zero."),
         example("nums = [0,0,0]", "[[0,0,0]]", "The three zeros form one distinct triplet.")]),
    "best-time-to-buy-and-sell-stock": verified(
        "best-time-to-buy-and-sell-stock", 121,
        "Given prices in chronological order, choose at most one day to buy a stock and a later day to sell it. Return the largest nonnegative profit from that single transaction. If no profitable sale is possible, return zero instead of making a losing transaction.",
        ["1 <= prices.length <= 10^5", "0 <= prices[i] <= 10^4"],
        [example("prices = [7,1,5,3,6,4]", "5", "Buying at 1 and later selling at 6 yields profit 5."),
         example("prices = [7,6,4,3,1]", "0", "Every later sale would lose money, so no trade is made.")]),
    "longest-substring-without-repeating-characters": verified(
        "longest-substring-without-repeating-characters", 3,
        "Given a string s, return the length of its longest contiguous substring whose characters are all different. A subsequence that skips positions does not qualify. Return zero when s is empty; all supplied letters, digits, symbols, and spaces are characters for this check.",
        ["0 <= s.length <= 10^5", "s may contain English letters, digits, symbols, and spaces."],
        [example('s = "abcabcbb"', "3", "For example, abc is a length-three substring with no repeated character."),
         example('s = "bbbbb"', "1", "Any one b is valid; adjacent b values repeat."),
         example('s = "pwwkew"', "3", "wke is contiguous and unique; skipping characters is not allowed.")]),
    "longest-repeating-character-replacement": verified(
        "longest-repeating-character-replacement", 424,
        "Given an uppercase-English-letter string s and an integer k, you may change up to k characters to any uppercase English letters. Return the maximum length of a contiguous substring that can consist of one repeated letter after those changes. Changes outside the chosen substring are unnecessary.",
        ["1 <= s.length <= 10^5", "s contains uppercase English letters only.",
         "0 <= k <= s.length"],
        [example('s = "ABAB", k = 2', "4", "Changing two letters can make all four characters equal."),
         example('s = "AABABBA", k = 1', "4", "A length-four block can be made identical with one change.")]),
    "valid-parentheses": verified(
        "valid-parentheses", 20,
        "Given a nonempty string s made only of round, square, and curly brackets, return true if every closing bracket matches an earlier unmatched opening bracket of the same type and brackets close in the proper nested order. Return false for a mismatch, premature closing bracket, or opening bracket left unclosed.",
        ["1 <= s.length <= 10^4", "s contains only the six bracket characters ()[]{}."],
        [example('s = "()"', "true"), example('s = "()[]{}"', "true"),
         example('s = "(]"', "false"), example('s = "([])"', "true"),
         example('s = "([)]"', "false")]),
    "min-stack": verified(
        "min-stack", 155,
        "Implement a MinStack object. Its constructor creates an empty stack; push(value) adds a value; pop() removes the top value; top() returns that value; and getMin() returns the smallest value currently stored. Each method must take constant time. Calls to pop, top, and getMin are guaranteed to occur only when the stack is nonempty. The example's operation and argument arrays are parallel, and constructor and void calls produce null results.",
        ["-2^31 <= value <= 2^31 - 1", "pop, top, and getMin are called only on nonempty stacks.",
         "At most 3 * 10^4 total calls are made to push, pop, top, and getMin."],
        [example('["MinStack","push","push","push","getMin","pop","top","getMin"]\n[[],[-2],[0],[-3],[],[],[],[]]',
                 "[null,null,null,null,-3,null,0,-2]",
                 "After pushing -2, 0, and -3, the minimum is -3. Popping -3 exposes top 0 and minimum -2.")],
        time_instruction="Required: every MinStack operation runs in O(1) time."),
    "daily-temperatures": verified(
        "daily-temperatures", 739,
        "Given one temperature for each day, return an array of equal length. At position i, report the number of later days until the first strictly warmer temperature; report zero if no later day is warmer.",
        ["1 <= temperatures.length <= 10^5", "30 <= temperatures[i] <= 100"],
        [example("temperatures = [73,74,75,71,69,72,76,73]", "[1,1,4,2,1,1,0,0]"),
         example("temperatures = [30,40,50,60]", "[1,1,1,0]"),
         example("temperatures = [30,60,90]", "[1,1,0]")]),
    "binary-search": verified(
        "binary-search", 704,
        "Given an ascending array nums of distinct integers and a target integer, return the zero-based index of target if it appears, or -1 if absent. The required algorithm must run in logarithmic time in the array length.",
        ["1 <= nums.length <= 10^4", "-10^4 < nums[i], target < 10^4",
         "All values in nums are distinct.", "nums is sorted in ascending order."],
        [example("nums = [-1,0,3,5,9,12], target = 9", "4", "The target 9 appears at index 4."),
         example("nums = [-1,0,3,5,9,12], target = 2", "-1", "The target is absent.")],
        time_instruction="Required: O(log n) runtime."),
    "search-in-rotated-sorted-array": verified(
        "search-in-rotated-sorted-array", 33,
        "Given an array of distinct integers that was ascending before a possible rotation, and a target, return the target's zero-based index in the current array or -1 if absent. The rotation offset is unknown and may be zero. The required search must run in logarithmic time.",
        ["1 <= nums.length <= 5000", "-10^4 <= nums[i] <= 10^4",
         "All nums values are distinct.", "nums was ascending before a possible rotation.",
         "-10^4 <= target <= 10^4"],
        [example("nums = [4,5,6,7,0,1,2], target = 0", "4"),
         example("nums = [4,5,6,7,0,1,2], target = 3", "-1"),
         example("nums = [1], target = 0", "-1")],
        time_instruction="Required: O(log n) runtime."),
    "reverse-linked-list": verified(
        "reverse-linked-list", 206,
        "Given the head of a singly linked list, reverse the direction of its links and return the head of the resulting list. A null head represents an empty list and should produce an empty result. Each node stores a value and a reference to the next node; the result contains the same values in reverse order.",
        ["The linked list has 0 to 5000 nodes.", "-5000 <= Node.val <= 5000"],
        [example("head = [1,2,3,4,5]", "[5,4,3,2,1]"),
         example("head = [1,2]", "[2,1]"), example("head = []", "[]")]),
    "merge-two-sorted-lists": verified(
        "merge-two-sorted-lists", 21,
        "Given the heads of two singly linked lists sorted in non-decreasing order, merge them by connecting their existing nodes into one sorted list and return its head. Either list may be empty. Preserve every input node and its value; the list notation in examples represents node chains, not arrays to return.",
        ["Each input list has 0 to 50 nodes.", "-100 <= Node.val <= 100",
         "Both input lists are sorted in non-decreasing order."],
        [example("list1 = [1,2,4], list2 = [1,3,4]", "[1,1,2,3,4,4]"),
         example("list1 = [], list2 = []", "[]"),
         example("list1 = [], list2 = [0]", "[0]")]),
    "maximum-depth-of-binary-tree": verified(
        "maximum-depth-of-binary-tree", 104,
        "Given a binary-tree root, return the number of nodes on the longest path from the root down to a leaf. An empty tree has depth zero. A tree node contains a value and optional left and right children; null entries in the example's level-order notation denote missing children.",
        ["The tree has 0 to 10^4 nodes.", "-100 <= Node.val <= 100"],
        [example("root = [3,9,20,null,null,15,7]", "3"),
         example("root = [1,null,2]", "2")]),
    "number-of-islands": verified(
        "number-of-islands", 200,
        "Given a nonempty rectangular grid of character '1' land cells and '0' water cells, return the number of connected land regions. Land connects only through shared horizontal or vertical edges, not diagonals. Treat the area beyond all four grid borders as water.",
        ["m == grid.length", "n == grid[i].length", "1 <= m, n <= 300",
         "Every grid[i][j] is the character '0' or '1'."],
        [example('grid = [["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]]', "1"),
         example('grid = [["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]', "3")]),
    "climbing-stairs": verified(
        "climbing-stairs", 70,
        "Given a staircase with n steps, return how many distinct ordered sequences of moves reach its top when each move climbs either one or two steps. Different move orders count as different ways; n is at least one.",
        ["1 <= n <= 45"],
        [example("n = 2", "2", "The move sequences are 1+1 and 2."),
         example("n = 3", "3", "The move sequences are 1+1+1, 1+2, and 2+1.")]),
}
