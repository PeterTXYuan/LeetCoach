SUPPORTED_LANGUAGES = {"python", "java", "javascript", "cpp"}

CURATED_MOCK_WARNING = (
    "This answer is a curated mock example. "
    "Review and test it before using."
)


class UnsupportedLanguageError(ValueError):
    pass


MOCK_SOLUTIONS = {
    ("two-sum", "brute-force"): {
        "explanation": "This mock solution follows the selected brute-force approach by checking each possible pair.",
        "timeComplexity": "O(n^2)",
        "spaceComplexity": "O(1)",
        "code": {
            "python": """class Solution:
    def twoSum(self, nums, target):
        # Mock answer: brute-force pair search.
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[i] + nums[j] == target:
                    return [i, j]
        return []""",
            "java": """class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Mock answer: brute-force pair search.
        for (int i = 0; i < nums.length; i++) {
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[i] + nums[j] == target) {
                    return new int[] { i, j };
                }
            }
        }
        return new int[] {};
    }
}""",
            "javascript": """var twoSum = function(nums, target) {
  // Mock answer: brute-force pair search.
  for (let i = 0; i < nums.length; i++) {
    for (let j = i + 1; j < nums.length; j++) {
      if (nums[i] + nums[j] === target) {
        return [i, j];
      }
    }
  }
  return [];
};""",
            "cpp": """class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // Mock answer: brute-force pair search.
        for (int i = 0; i < nums.size(); i++) {
            for (int j = i + 1; j < nums.size(); j++) {
                if (nums[i] + nums[j] == target) {
                    return {i, j};
                }
            }
        }
        return {};
    }
};""",
        },
    },
    ("two-sum", "hash-map"): {
        "explanation": "This mock solution follows the selected one-pass hash map approach by storing seen values and checking complements.",
        "timeComplexity": "O(n)",
        "spaceComplexity": "O(n)",
        "code": {
            "python": """class Solution:
    def twoSum(self, nums, target):
        # Mock answer: one-pass hash map.
        seen = {}
        for i, value in enumerate(nums):
            complement = target - value
            if complement in seen:
                return [seen[complement], i]
            seen[value] = i
        return []""",
            "java": """class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Mock answer: one-pass hash map.
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) {
                return new int[] { seen.get(complement), i };
            }
            seen.put(nums[i], i);
        }
        return new int[] {};
    }
}""",
            "javascript": """var twoSum = function(nums, target) {
  // Mock answer: one-pass hash map.
  const seen = new Map();
  for (let i = 0; i < nums.length; i++) {
    const complement = target - nums[i];
    if (seen.has(complement)) {
      return [seen.get(complement), i];
    }
    seen.set(nums[i], i);
  }
  return [];
};""",
            "cpp": """class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // Mock answer: one-pass hash map.
        unordered_map<int, int> seen;
        for (int i = 0; i < nums.size(); i++) {
            int complement = target - nums[i];
            if (seen.count(complement)) {
                return {seen[complement], i};
            }
            seen[nums[i]] = i;
        }
        return {};
    }
};""",
        },
    },
    ("valid-parentheses", "replace-pairs"): {
        "explanation": "This mock solution follows repeated pair removal by shrinking valid adjacent bracket pairs until no changes remain.",
        "timeComplexity": "O(n^2)",
        "spaceComplexity": "O(n)",
        "code": {
            "python": """class Solution:
    def isValid(self, s):
        # Mock answer: repeatedly remove resolved pairs.
        previous = None
        while previous != s:
            previous = s
            s = s.replace("()", "").replace("[]", "").replace("{}", "")
        return s == ''""",
            "java": """class Solution {
    public boolean isValid(String s) {
        // Mock answer: repeatedly remove resolved pairs.
        String previous;
        do {
            previous = s;
            s = s.replace("()", "").replace("[]", "").replace("{}", "");
        } while (!s.equals(previous));
        return s.isEmpty();
    }
}""",
            "javascript": """var isValid = function(s) {
  // Mock answer: repeatedly remove resolved pairs.
  let previous;
  do {
    previous = s;
    s = s.replaceAll("()", "").replaceAll("[]", "").replaceAll("{}", "");
  } while (s !== previous);
  return s.length === 0;
};""",
            "cpp": """class Solution {
public:
    bool isValid(string s) {
        // Mock answer: repeatedly remove resolved pairs.
        string previous;
        do {
            previous = s;
            erasePairs(s, "()");
            erasePairs(s, "[]");
            erasePairs(s, "{}");
        } while (s != previous);
        return s.empty();
    }

    void erasePairs(string& s, const string& pair) {
        size_t pos;
        while ((pos = s.find(pair)) != string::npos) {
            s.erase(pos, 2);
        }
    }
};""",
        },
    },
    ("valid-parentheses", "stack"): {
        "explanation": "This mock solution follows the selected stack approach by matching each closing bracket with the most recent unresolved opener.",
        "timeComplexity": "O(n)",
        "spaceComplexity": "O(n)",
        "code": {
            "python": """class Solution:
    def isValid(self, s):
        # Mock answer: stack of opening brackets.
        pairs = {")": "(", "]": "[", "}": "{"}
        stack = []
        for ch in s:
            if ch in pairs.values():
                stack.append(ch)
            elif not stack or stack.pop() != pairs[ch]:
                return False
        return not stack""",
            "java": """class Solution {
    public boolean isValid(String s) {
        // Mock answer: stack of opening brackets.
        Map<Character, Character> pairs = Map.of(')', '(', ']', '[', '}', '{');
        Deque<Character> stack = new ArrayDeque<>();
        for (char ch : s.toCharArray()) {
            if (pairs.containsValue(ch)) {
                stack.push(ch);
            } else if (stack.isEmpty() || stack.pop() != pairs.get(ch)) {
                return false;
            }
        }
        return stack.isEmpty();
    }
}""",
            "javascript": """var isValid = function(s) {
  // Mock answer: stack of opening brackets.
  const pairs = { ")": "(", "]": "[", "}": "{" };
  const stack = [];
  for (const ch of s) {
    if (ch === "(" || ch === "[" || ch === "{") {
      stack.push(ch);
    } else if (stack.pop() !== pairs[ch]) {
      return false;
    }
  }
  return stack.length === 0;
};""",
            "cpp": """class Solution {
public:
    bool isValid(string s) {
        // Mock answer: stack of opening brackets.
        unordered_map<char, char> pairs = {{')', '('}, {']', '['}, {'}', '{'}};
        stack<char> open;
        for (char ch : s) {
            if (ch == '(' || ch == '[' || ch == '{') {
                open.push(ch);
            } else if (open.empty() || open.top() != pairs[ch]) {
                return false;
            } else {
                open.pop();
            }
        }
        return open.empty();
    }
};""",
        },
    },
    ("longest-substring-without-repeating-characters", "brute-force-substrings"): {
        "explanation": "This mock solution follows the selected brute-force substring approach by testing every candidate substring for duplicates.",
        "timeComplexity": "O(n^3)",
        "spaceComplexity": "O(min(n, alphabet))",
        "code": {
            "python": """class Solution:
    def lengthOfLongestSubstring(self, s):
        # Mock answer: check every substring.
        best = 0
        for left in range(len(s)):
            for right in range(left, len(s)):
                seen = set()
                valid = True
                for i in range(left, right + 1):
                    if s[i] in seen:
                        valid = False
                        break
                    seen.add(s[i])
                if valid:
                    best = max(best, right - left + 1)
        return best""",
            "java": """class Solution {
    public int lengthOfLongestSubstring(String s) {
        // Mock answer: check every substring.
        int best = 0;
        for (int left = 0; left < s.length(); left++) {
            for (int right = left; right < s.length(); right++) {
                Set<Character> seen = new HashSet<>();
                boolean valid = true;
                for (int i = left; i <= right; i++) {
                    if (!seen.add(s.charAt(i))) {
                        valid = false;
                        break;
                    }
                }
                if (valid) best = Math.max(best, right - left + 1);
            }
        }
        return best;
    }
}""",
            "javascript": """var lengthOfLongestSubstring = function(s) {
  // Mock answer: check every substring.
  let best = 0;
  for (let left = 0; left < s.length; left++) {
    for (let right = left; right < s.length; right++) {
      const seen = new Set();
      let valid = true;
      for (let i = left; i <= right; i++) {
        if (seen.has(s[i])) {
          valid = false;
          break;
        }
        seen.add(s[i]);
      }
      if (valid) best = Math.max(best, right - left + 1);
    }
  }
  return best;
};""",
            "cpp": """class Solution {
public:
    int lengthOfLongestSubstring(string s) {
        // Mock answer: check every substring.
        int best = 0;
        for (int left = 0; left < s.size(); left++) {
            for (int right = left; right < s.size(); right++) {
                unordered_set<char> seen;
                bool valid = true;
                for (int i = left; i <= right; i++) {
                    if (seen.count(s[i])) {
                        valid = false;
                        break;
                    }
                    seen.insert(s[i]);
                }
                if (valid) best = max(best, right - left + 1);
            }
        }
        return best;
    }
};""",
        },
    },
    ("longest-substring-without-repeating-characters", "sliding-window-set"): {
        "explanation": "This mock solution follows the selected sliding-window set approach by keeping the current window duplicate-free.",
        "timeComplexity": "O(n)",
        "spaceComplexity": "O(min(n, alphabet))",
        "code": {
            "python": """class Solution:
    def lengthOfLongestSubstring(self, s):
        # Mock answer: sliding window with set.
        seen = set()
        left = 0
        best = 0
        for right, ch in enumerate(s):
            while ch in seen:
                seen.remove(s[left])
                left += 1
            seen.add(ch)
            best = max(best, right - left + 1)
        return best""",
            "java": """class Solution {
    public int lengthOfLongestSubstring(String s) {
        // Mock answer: sliding window with set.
        Set<Character> seen = new HashSet<>();
        int left = 0;
        int best = 0;
        for (int right = 0; right < s.length(); right++) {
            char ch = s.charAt(right);
            while (seen.contains(ch)) {
                seen.remove(s.charAt(left));
                left++;
            }
            seen.add(ch);
            best = Math.max(best, right - left + 1);
        }
        return best;
    }
}""",
            "javascript": """var lengthOfLongestSubstring = function(s) {
  // Mock answer: sliding window with set.
  const seen = new Set();
  let left = 0;
  let best = 0;
  for (let right = 0; right < s.length; right++) {
    while (seen.has(s[right])) {
      seen.delete(s[left]);
      left++;
    }
    seen.add(s[right]);
    best = Math.max(best, right - left + 1);
  }
  return best;
};""",
            "cpp": """class Solution {
public:
    int lengthOfLongestSubstring(string s) {
        // Mock answer: sliding window with set.
        unordered_set<char> seen;
        int left = 0;
        int best = 0;
        for (int right = 0; right < s.size(); right++) {
            while (seen.count(s[right])) {
                seen.erase(s[left]);
                left++;
            }
            seen.insert(s[right]);
            best = max(best, right - left + 1);
        }
        return best;
    }
};""",
        },
    },
    ("longest-substring-without-repeating-characters", "sliding-window-index-map"): {
        "explanation": "This mock solution follows the selected last-seen index approach by jumping the left boundary past repeated characters.",
        "timeComplexity": "O(n)",
        "spaceComplexity": "O(min(n, alphabet))",
        "code": {
            "python": """class Solution:
    def lengthOfLongestSubstring(self, s):
        # Mock answer: sliding window with last-seen index.
        last_seen = {}
        left = 0
        best = 0
        for right, ch in enumerate(s):
            if ch in last_seen and last_seen[ch] >= left:
                left = last_seen[ch] + 1
            last_seen[ch] = right
            best = max(best, right - left + 1)
        return best""",
            "java": """class Solution {
    public int lengthOfLongestSubstring(String s) {
        // Mock answer: sliding window with last-seen index.
        Map<Character, Integer> lastSeen = new HashMap<>();
        int left = 0;
        int best = 0;
        for (int right = 0; right < s.length(); right++) {
            char ch = s.charAt(right);
            if (lastSeen.containsKey(ch) && lastSeen.get(ch) >= left) {
                left = lastSeen.get(ch) + 1;
            }
            lastSeen.put(ch, right);
            best = Math.max(best, right - left + 1);
        }
        return best;
    }
}""",
            "javascript": """var lengthOfLongestSubstring = function(s) {
  // Mock answer: sliding window with last-seen index.
  const lastSeen = new Map();
  let left = 0;
  let best = 0;
  for (let right = 0; right < s.length; right++) {
    const ch = s[right];
    if (lastSeen.has(ch) && lastSeen.get(ch) >= left) {
      left = lastSeen.get(ch) + 1;
    }
    lastSeen.set(ch, right);
    best = Math.max(best, right - left + 1);
  }
  return best;
};""",
            "cpp": """class Solution {
public:
    int lengthOfLongestSubstring(string s) {
        // Mock answer: sliding window with last-seen index.
        unordered_map<char, int> lastSeen;
        int left = 0;
        int best = 0;
        for (int right = 0; right < s.size(); right++) {
            char ch = s[right];
            if (lastSeen.count(ch) && lastSeen[ch] >= left) {
                left = lastSeen[ch] + 1;
            }
            lastSeen[ch] = right;
            best = max(best, right - left + 1);
        }
        return best;
    }
};""",
        },
    },
}


def generate_approach_solution(problem, approach, language):
    normalized_language = language.lower()

    if normalized_language not in SUPPORTED_LANGUAGES:
        raise UnsupportedLanguageError(language)

    mock_solution = MOCK_SOLUTIONS[(problem["slug"], approach["id"])]

    return {
        "slug": problem["slug"],
        "approachId": approach["id"],
        "language": normalized_language,
        "isAiGenerated": False,
        "warning": CURATED_MOCK_WARNING,
        "code": mock_solution["code"][normalized_language],
        "explanation": mock_solution["explanation"],
        "timeComplexity": mock_solution["timeComplexity"],
        "spaceComplexity": mock_solution["spaceComplexity"],
    }
