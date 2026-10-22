"""Official LeetCode facts verified for the 20-problem catalog expansion.

Source: https://leetcode.com/problems/{slug}/ (GraphQL question metadata).
Example inputs/outputs, constraints, and signature shells match the official pages.
Descriptions and explanations are original editorial prose.
"""

CATALOG_40_VERIFIED_AT = '2026-10-22T03:45:59+00:00'

NEW_FACTS = {'product-of-array-except-self': {'title': 'Product of Array Except Self',
                                  'difficulty': 'Medium',
                                  'leetcodeNumber': 238,
                                  'constraints': ['2 <= nums.length <= 10^5',
                                                  '-30 <= nums[i] <= 30',
                                                  'The input is generated such that answer[i] is '
                                                  'guaranteed to fit in a 32-bit integer.'],
                                  'examples': [{'input': 'nums = [1,2,3,4]',
                                                'output': '[24,12,8,6]',
                                                'explanation': None},
                                               {'input': 'nums = [-1,1,0,-3,3]',
                                                'output': '[0,0,9,0,0]',
                                                'explanation': None}],
                                  'submissionTemplates': {'python': 'class Solution:\n'
                                                                    '    def productExceptSelf(self, '
                                                                    'nums: list[int]) -> list[int]:\n'
                                                                    '        pass',
                                                          'java': 'class Solution {\n'
                                                                  '    public int[] '
                                                                  'productExceptSelf(int[] nums) {\n'
                                                                  '\n'
                                                                  '    }\n'
                                                                  '}',
                                                          'javascript': 'var productExceptSelf = '
                                                                        'function(nums) {\n'
                                                                        '\n'
                                                                        '};',
                                                          'cpp': 'class Solution {\n'
                                                                 'public:\n'
                                                                 '    vector<int> '
                                                                 'productExceptSelf(vector<int>& nums) '
                                                                 '{\n'
                                                                 '\n'
                                                                 '    }\n'
                                                                 '};'}},
 'top-k-frequent-elements': {'title': 'Top K Frequent Elements',
                             'difficulty': 'Medium',
                             'leetcodeNumber': 347,
                             'constraints': ['1 <= nums.length <= 10^5',
                                             '-10^4 <= nums[i] <= 10^4',
                                             'k is in the range [1, the number of unique elements in '
                                             'the array].',
                                             'It is guaranteed that the answer is unique.'],
                             'examples': [{'input': 'nums = [1,1,1,2,2,3], k = 2',
                                           'output': '[1,2]',
                                           'explanation': None},
                                          {'input': 'nums = [1], k = 1',
                                           'output': '[1]',
                                           'explanation': None},
                                          {'input': 'nums = [1,2,1,2,1,2,3,1,3,2], k = 2',
                                           'output': '[1,2]',
                                           'explanation': None}],
                             'submissionTemplates': {'python': 'class Solution:\n'
                                                               '    def topKFrequent(self, nums: '
                                                               'list[int], k: int) -> list[int]:\n'
                                                               '        pass',
                                                     'java': 'class Solution {\n'
                                                             '    public int[] topKFrequent(int[] nums, '
                                                             'int k) {\n'
                                                             '\n'
                                                             '    }\n'
                                                             '}',
                                                     'javascript': 'var topKFrequent = function(nums, '
                                                                   'k) {\n'
                                                                   '\n'
                                                                   '};',
                                                     'cpp': 'class Solution {\n'
                                                            'public:\n'
                                                            '    vector<int> topKFrequent(vector<int>& '
                                                            'nums, int k) {\n'
                                                            '\n'
                                                            '    }\n'
                                                            '};'}},
 'longest-consecutive-sequence': {'title': 'Longest Consecutive Sequence',
                                  'difficulty': 'Medium',
                                  'leetcodeNumber': 128,
                                  'constraints': ['0 <= nums.length <= 10^5',
                                                  '-10^9 <= nums[i] <= 10^9'],
                                  'examples': [{'input': 'nums = [100,4,200,1,3,2]',
                                                'output': '4',
                                                'explanation': 'The run 1, 2, 3, 4 has four distinct '
                                                               'consecutive values.'},
                                               {'input': 'nums = [0,3,7,2,5,8,4,6,0,1]',
                                                'output': '9',
                                                'explanation': None},
                                               {'input': 'nums = [1,0,1,2]',
                                                'output': '3',
                                                'explanation': None}],
                                  'submissionTemplates': {'python': 'class Solution:\n'
                                                                    '    def longestConsecutive(self, '
                                                                    'nums: list[int]) -> int:\n'
                                                                    '        pass',
                                                          'java': 'class Solution {\n'
                                                                  '    public int '
                                                                  'longestConsecutive(int[] nums) {\n'
                                                                  '\n'
                                                                  '    }\n'
                                                                  '}',
                                                          'javascript': 'var longestConsecutive = '
                                                                        'function(nums) {\n'
                                                                        '\n'
                                                                        '};',
                                                          'cpp': 'class Solution {\n'
                                                                 'public:\n'
                                                                 '    int '
                                                                 'longestConsecutive(vector<int>& nums) '
                                                                 '{\n'
                                                                 '\n'
                                                                 '    }\n'
                                                                 '};'}},
 'valid-sudoku': {'title': 'Valid Sudoku',
                  'difficulty': 'Medium',
                  'leetcodeNumber': 36,
                  'constraints': ['board.length == 9',
                                  'board[i].length == 9',
                                  "board[i][j] is a digit 1-9 or '.'."],
                  'examples': [{'input': 'board = \n'
                                         '[["5","3",".",".","7",".",".",".","."]\n'
                                         ',["6",".",".","1","9","5",".",".","."]\n'
                                         ',[".","9","8",".",".",".",".","6","."]\n'
                                         ',["8",".",".",".","6",".",".",".","3"]\n'
                                         ',["4",".",".","8",".","3",".",".","1"]\n'
                                         ',["7",".",".",".","2",".",".",".","6"]\n'
                                         ',[".","6",".",".",".",".","2","8","."]\n'
                                         ',[".",".",".","4","1","9",".",".","5"]\n'
                                         ',[".",".",".",".","8",".",".","7","9"]]',
                                'output': 'true',
                                'explanation': None},
                               {'input': 'board = \n'
                                         '[["8","3",".",".","7",".",".",".","."]\n'
                                         ',["6",".",".","1","9","5",".",".","."]\n'
                                         ',[".","9","8",".",".",".",".","6","."]\n'
                                         ',["8",".",".",".","6",".",".",".","3"]\n'
                                         ',["4",".",".","8",".","3",".",".","1"]\n'
                                         ',["7",".",".",".","2",".",".",".","6"]\n'
                                         ',[".","6",".",".",".",".","2","8","."]\n'
                                         ',[".",".",".","4","1","9",".",".","5"]\n'
                                         ',[".",".",".",".","8",".",".","7","9"]]',
                                'output': 'false',
                                'explanation': 'Changing the upper-left entry to 8 repeats an 8 within '
                                               'its 3-by-3 box.'}],
                  'submissionTemplates': {'python': 'class Solution:\n'
                                                    '    def isValidSudoku(self, board: '
                                                    'list[list[str]]) -> bool:\n'
                                                    '        pass',
                                          'java': 'class Solution {\n'
                                                  '    public boolean isValidSudoku(char[][] board) {\n'
                                                  '\n'
                                                  '    }\n'
                                                  '}',
                                          'javascript': 'var isValidSudoku = function(board) {\n\n};',
                                          'cpp': 'class Solution {\n'
                                                 'public:\n'
                                                 '    bool isValidSudoku(vector<vector<char>>& board) '
                                                 '{\n'
                                                 '\n'
                                                 '    }\n'
                                                 '};'}},
 'container-with-most-water': {'title': 'Container With Most Water',
                               'difficulty': 'Medium',
                               'leetcodeNumber': 11,
                               'constraints': ['n == height.length',
                                               '2 <= n <= 10^5',
                                               '0 <= height[i] <= 10^4'],
                               'examples': [{'input': 'height = [1,8,6,2,5,4,8,3,7]',
                                             'output': '49',
                                             'explanation': 'The lines at positions 1 and 8 enclose '
                                                            'width 7 with limiting height 7, giving '
                                                            'area 49.'},
                                            {'input': 'height = [1,1]',
                                             'output': '1',
                                             'explanation': None}],
                               'submissionTemplates': {'python': 'class Solution:\n'
                                                                 '    def maxArea(self, height: '
                                                                 'list[int]) -> int:\n'
                                                                 '        pass',
                                                       'java': 'class Solution {\n'
                                                               '    public int maxArea(int[] height) {\n'
                                                               '\n'
                                                               '    }\n'
                                                               '}',
                                                       'javascript': 'var maxArea = function(height) {\n'
                                                                     '\n'
                                                                     '};',
                                                       'cpp': 'class Solution {\n'
                                                              'public:\n'
                                                              '    int maxArea(vector<int>& height) {\n'
                                                              '\n'
                                                              '    }\n'
                                                              '};'}},
 'evaluate-reverse-polish-notation': {'title': 'Evaluate Reverse Polish Notation',
                                      'difficulty': 'Medium',
                                      'leetcodeNumber': 150,
                                      'constraints': ['1 <= tokens.length <= 10^4',
                                                      'tokens[i] is either an operator: "+", "-", "*", '
                                                      'or "/", or an integer in the range [-200, 200].'],
                                      'examples': [{'input': 'tokens = ["2","1","+","3","*"]',
                                                    'output': '9',
                                                    'explanation': 'Add 2 and 1, then multiply their '
                                                                   'result by 3.'},
                                                   {'input': 'tokens = ["4","13","5","/","+"]',
                                                    'output': '6',
                                                    'explanation': 'Divide 13 by 5 with truncation, '
                                                                   'then add 4.'},
                                                   {'input': 'tokens = '
                                                             '["10","6","9","3","+","-11","*","/","*","17","+","5","+"]',
                                                    'output': '22',
                                                    'explanation': 'The nested operations eventually '
                                                                   'produce 0 for the division term, '
                                                                   'followed by 17 + 5 = 22.'}],
                                      'submissionTemplates': {'python': 'class Solution:\n'
                                                                        '    def evalRPN(self, tokens: '
                                                                        'list[str]) -> int:\n'
                                                                        '        pass',
                                                              'java': 'class Solution {\n'
                                                                      '    public int evalRPN(String[] '
                                                                      'tokens) {\n'
                                                                      '\n'
                                                                      '    }\n'
                                                                      '}',
                                                              'javascript': 'var evalRPN = '
                                                                            'function(tokens) {\n'
                                                                            '\n'
                                                                            '};',
                                                              'cpp': 'class Solution {\n'
                                                                     'public:\n'
                                                                     '    int evalRPN(vector<string>& '
                                                                     'tokens) {\n'
                                                                     '\n'
                                                                     '    }\n'
                                                                     '};'}},
 'generate-parentheses': {'title': 'Generate Parentheses',
                          'difficulty': 'Medium',
                          'leetcodeNumber': 22,
                          'constraints': ['1 <= n <= 8'],
                          'examples': [{'input': 'n = 3',
                                        'output': '["((()))","(()())","(())()","()(())","()()()"]',
                                        'explanation': None},
                                       {'input': 'n = 1', 'output': '["()"]', 'explanation': None}],
                          'submissionTemplates': {'python': 'class Solution:\n'
                                                            '    def generateParenthesis(self, n: int) '
                                                            '-> list[str]:\n'
                                                            '        pass',
                                                  'java': 'class Solution {\n'
                                                          '    public List<String> '
                                                          'generateParenthesis(int n) {\n'
                                                          '\n'
                                                          '    }\n'
                                                          '}',
                                                  'javascript': 'var generateParenthesis = function(n) '
                                                                '{\n'
                                                                '\n'
                                                                '};',
                                                  'cpp': 'class Solution {\n'
                                                         'public:\n'
                                                         '    vector<string> generateParenthesis(int n) '
                                                         '{\n'
                                                         '\n'
                                                         '    }\n'
                                                         '};'}},
 'car-fleet': {'title': 'Car Fleet',
               'difficulty': 'Medium',
               'leetcodeNumber': 853,
               'constraints': ['n == position.length == speed.length',
                               '1 <= n <= 10^5',
                               '0 < target <= 10^6',
                               '0 <= position[i] < target',
                               'All the values of position are unique.',
                               '0 < speed[i] <= 10^6'],
               'examples': [{'input': 'target = 12, position = [10,8,0,5,3], speed = [2,4,1,1,3]',
                             'output': '3',
                             'explanation': 'The cars from 10 and 8 meet at the target; the cars from 5 '
                                            'and 3 join earlier; the car from 0 stays alone.'},
                            {'input': 'target = 10, position = [3], speed = [3]',
                             'output': '1',
                             'explanation': 'The sole car makes one fleet.'},
                            {'input': 'target = 100, position = [0,2,4], speed = [4,2,1]',
                             'output': '1',
                             'explanation': 'The cars from 0 and 2 join at mile 4, then catch the car '
                                            'from mile 4; all three arrive together.'}],
               'submissionTemplates': {'python': 'class Solution:\n'
                                                 '    def carFleet(self, target: int, position: '
                                                 'list[int], speed: list[int]) -> int:\n'
                                                 '        pass',
                                       'java': 'class Solution {\n'
                                               '    public int carFleet(int target, int[] position, '
                                               'int[] speed) {\n'
                                               '\n'
                                               '    }\n'
                                               '}',
                                       'javascript': 'var carFleet = function(target, position, speed) '
                                                     '{\n'
                                                     '\n'
                                                     '};',
                                       'cpp': 'class Solution {\n'
                                              'public:\n'
                                              '    int carFleet(int target, vector<int>& position, '
                                              'vector<int>& speed) {\n'
                                              '\n'
                                              '    }\n'
                                              '};'}},
 'find-minimum-in-rotated-sorted-array': {'title': 'Find Minimum in Rotated Sorted Array',
                                          'difficulty': 'Medium',
                                          'leetcodeNumber': 153,
                                          'constraints': ['n == nums.length',
                                                          '1 <= n <= 5000',
                                                          '-5000 <= nums[i] <= 5000',
                                                          'All the integers of nums are unique.',
                                                          'nums is sorted and rotated between 1 and n '
                                                          'times.'],
                                          'examples': [{'input': 'nums = [3,4,5,1,2]',
                                                        'output': '1',
                                                        'explanation': 'Rotating [1,2,3,4,5] three '
                                                                       'times gives this array.'},
                                                       {'input': 'nums = [4,5,6,7,0,1,2]',
                                                        'output': '0',
                                                        'explanation': 'The sorted source '
                                                                       '[0,1,2,4,5,6,7] was rotated '
                                                                       'four times.'},
                                                       {'input': 'nums = [11,13,15,17]',
                                                        'output': '11',
                                                        'explanation': 'Rotating by the full array '
                                                                       'length restores the original '
                                                                       'sorted order.'}],
                                          'submissionTemplates': {'python': 'class Solution:\n'
                                                                            '    def findMin(self, '
                                                                            'nums: list[int]) -> int:\n'
                                                                            '        pass',
                                                                  'java': 'class Solution {\n'
                                                                          '    public int findMin(int[] '
                                                                          'nums) {\n'
                                                                          '\n'
                                                                          '    }\n'
                                                                          '}',
                                                                  'javascript': 'var findMin = '
                                                                                'function(nums) {\n'
                                                                                '\n'
                                                                                '};',
                                                                  'cpp': 'class Solution {\n'
                                                                         'public:\n'
                                                                         '    int findMin(vector<int>& '
                                                                         'nums) {\n'
                                                                         '\n'
                                                                         '    }\n'
                                                                         '};'}},
 'search-a-2d-matrix': {'title': 'Search a 2D Matrix',
                        'difficulty': 'Medium',
                        'leetcodeNumber': 74,
                        'constraints': ['m == matrix.length',
                                        'n == matrix[i].length',
                                        '1 <= m, n <= 100',
                                        '-10^4 <= matrix[i][j], target <= 10^4'],
                        'examples': [{'input': 'matrix = [[1,3,5,7],[10,11,16,20],[23,30,34,60]], '
                                               'target = 3',
                                      'output': 'true',
                                      'explanation': None},
                                     {'input': 'matrix = [[1,3,5,7],[10,11,16,20],[23,30,34,60]], '
                                               'target = 13',
                                      'output': 'false',
                                      'explanation': None}],
                        'submissionTemplates': {'python': 'class Solution:\n'
                                                          '    def searchMatrix(self, matrix: '
                                                          'list[list[int]], target: int) -> bool:\n'
                                                          '        pass',
                                                'java': 'class Solution {\n'
                                                        '    public boolean searchMatrix(int[][] '
                                                        'matrix, int target) {\n'
                                                        '\n'
                                                        '    }\n'
                                                        '}',
                                                'javascript': 'var searchMatrix = function(matrix, '
                                                              'target) {\n'
                                                              '\n'
                                                              '};',
                                                'cpp': 'class Solution {\n'
                                                       'public:\n'
                                                       '    bool searchMatrix(vector<vector<int>>& '
                                                       'matrix, int target) {\n'
                                                       '\n'
                                                       '    }\n'
                                                       '};'}},
 'koko-eating-bananas': {'title': 'Koko Eating Bananas',
                         'difficulty': 'Medium',
                         'leetcodeNumber': 875,
                         'constraints': ['1 <= piles.length <= 10^4',
                                         'piles.length <= h <= 10^9',
                                         '1 <= piles[i] <= 10^9'],
                         'examples': [{'input': 'piles = [3,6,7,11], h = 8',
                                       'output': '4',
                                       'explanation': None},
                                      {'input': 'piles = [30,11,23,4,20], h = 5',
                                       'output': '30',
                                       'explanation': None},
                                      {'input': 'piles = [30,11,23,4,20], h = 6',
                                       'output': '23',
                                       'explanation': None}],
                         'submissionTemplates': {'python': 'class Solution:\n'
                                                           '    def minEatingSpeed(self, piles: '
                                                           'list[int], h: int) -> int:\n'
                                                           '        pass',
                                                 'java': 'class Solution {\n'
                                                         '    public int minEatingSpeed(int[] piles, '
                                                         'int h) {\n'
                                                         '\n'
                                                         '    }\n'
                                                         '}',
                                                 'javascript': 'var minEatingSpeed = function(piles, h) '
                                                               '{\n'
                                                               '\n'
                                                               '};',
                                                 'cpp': 'class Solution {\n'
                                                        'public:\n'
                                                        '    int minEatingSpeed(vector<int>& piles, int '
                                                        'h) {\n'
                                                        '\n'
                                                        '    }\n'
                                                        '};'}},
 'time-based-key-value-store': {'title': 'Time Based Key-Value Store',
                                'difficulty': 'Medium',
                                'leetcodeNumber': 981,
                                'constraints': ['1 <= key.length, value.length <= 100',
                                                'key and value consist of lowercase English letters and '
                                                'digits.',
                                                '1 <= timestamp <= 10^7',
                                                'All the timestamps timestamp of set are strictly '
                                                'increasing.',
                                                'At most 2 * 10^5 calls will be made to set and get.'],
                                'examples': [{'input': '["TimeMap", "set", "get", "get", "set", "get", '
                                                       '"get"]\n'
                                                       '[[], ["foo", "bar", 1], ["foo", 1], ["foo", 3], '
                                                       '["foo", "bar2", 4], ["foo", 4], ["foo", 5]]',
                                              'output': '[null, null, "bar", "bar", null, "bar2", '
                                                        '"bar2"]',
                                              'explanation': 'The first set makes bar available at '
                                                             'times 1 and 3; the later set changes the '
                                                             'answer to bar2 from time 4 onward.'}],
                                'submissionTemplates': {'python': 'class TimeMap:\n'
                                                                  '    def __init__(self):\n'
                                                                  '        pass\n'
                                                                  '\n'
                                                                  '    def set(self, key: str, value: '
                                                                  'str, timestamp: int) -> None:\n'
                                                                  '        pass\n'
                                                                  '\n'
                                                                  '    def get(self, key: str, '
                                                                  'timestamp: int) -> str:\n'
                                                                  '        pass',
                                                        'java': 'class TimeMap {\n'
                                                                '    public TimeMap() {\n'
                                                                '\n'
                                                                '    }\n'
                                                                '\n'
                                                                '    public void set(String key, String '
                                                                'value, int timestamp) {\n'
                                                                '\n'
                                                                '    }\n'
                                                                '\n'
                                                                '    public String get(String key, int '
                                                                'timestamp) {\n'
                                                                '\n'
                                                                '    }\n'
                                                                '}',
                                                        'javascript': 'var TimeMap = function() {\n'
                                                                      '\n'
                                                                      '};\n'
                                                                      '\n'
                                                                      'TimeMap.prototype.set = '
                                                                      'function(key, value, timestamp) '
                                                                      '{\n'
                                                                      '\n'
                                                                      '};\n'
                                                                      '\n'
                                                                      'TimeMap.prototype.get = '
                                                                      'function(key, timestamp) {\n'
                                                                      '\n'
                                                                      '};',
                                                        'cpp': 'class TimeMap {\n'
                                                               'public: TimeMap() {\n'
                                                               '\n'
                                                               '    }\n'
                                                               '\n'
                                                               '    void set(string key, string value, '
                                                               'int timestamp) {\n'
                                                               '\n'
                                                               '    }\n'
                                                               '\n'
                                                               '    string get(string key, int '
                                                               'timestamp) {\n'
                                                               '\n'
                                                               '    }\n'
                                                               '};'}},
 'permutation-in-string': {'title': 'Permutation in String',
                           'difficulty': 'Medium',
                           'leetcodeNumber': 567,
                           'constraints': ['1 <= s1.length, s2.length <= 10^4',
                                           's1 and s2 consist of lowercase English letters.'],
                           'examples': [{'input': 's1 = "ab", s2 = "eidbaooo"',
                                         'output': 'true',
                                         'explanation': 'The contiguous substring "ba" rearranges the '
                                                        'two characters of s1.'},
                                        {'input': 's1 = "ab", s2 = "eidboaoo"',
                                         'output': 'false',
                                         'explanation': None}],
                           'submissionTemplates': {'python': 'class Solution:\n'
                                                             '    def checkInclusion(self, s1: str, s2: '
                                                             'str) -> bool:\n'
                                                             '        pass',
                                                   'java': 'class Solution {\n'
                                                           '    public boolean checkInclusion(String '
                                                           's1, String s2) {\n'
                                                           '\n'
                                                           '    }\n'
                                                           '}',
                                                   'javascript': 'var checkInclusion = function(s1, s2) '
                                                                 '{\n'
                                                                 '\n'
                                                                 '};',
                                                   'cpp': 'class Solution {\n'
                                                          'public:\n'
                                                          '    bool checkInclusion(string s1, string '
                                                          's2) {\n'
                                                          '\n'
                                                          '    }\n'
                                                          '};'}},
 'invert-binary-tree': {'title': 'Invert Binary Tree',
                        'difficulty': 'Easy',
                        'leetcodeNumber': 226,
                        'constraints': ['The number of nodes in the tree is in the range [0, 100].',
                                        '-100 <= Node.val <= 100'],
                        'examples': [{'input': 'root = [4,2,7,1,3,6,9]',
                                      'output': '[4,7,2,9,6,3,1]',
                                      'explanation': None},
                                     {'input': 'root = [2,1,3]',
                                      'output': '[2,3,1]',
                                      'explanation': None},
                                     {'input': 'root = []', 'output': '[]', 'explanation': None}],
                        'submissionTemplates': {'python': '# LeetCode provides TreeNode with val, left, '
                                                          'and right fields.\n'
                                                          'class Solution:\n'
                                                          '    def invertTree(self, root: TreeNode | '
                                                          'None) -> TreeNode | None:\n'
                                                          '        pass',
                                                'java': '// LeetCode provides TreeNode with val, left, '
                                                        'and right fields.\n'
                                                        'class Solution {\n'
                                                        '    public TreeNode invertTree(TreeNode root) '
                                                        '{\n'
                                                        '\n'
                                                        '    }\n'
                                                        '}',
                                                'javascript': '// LeetCode provides TreeNode with val, '
                                                              'left, and right fields.\n'
                                                              'var invertTree = function(root) {\n'
                                                              '\n'
                                                              '};',
                                                'cpp': '// LeetCode provides TreeNode with val, left, '
                                                       'and right fields.\n'
                                                       'class Solution {\n'
                                                       'public:\n'
                                                       '    TreeNode* invertTree(TreeNode* root) {\n'
                                                       '\n'
                                                       '    }\n'
                                                       '};'}},
 'same-tree': {'title': 'Same Tree',
               'difficulty': 'Easy',
               'leetcodeNumber': 100,
               'constraints': ['The number of nodes in both trees is in the range [0, 100].',
                               '-10^4 <= Node.val <= 10^4'],
               'examples': [{'input': 'p = [1,2,3], q = [1,2,3]', 'output': 'true', 'explanation': None},
                            {'input': 'p = [1,2], q = [1,null,2]',
                             'output': 'false',
                             'explanation': None},
                            {'input': 'p = [1,2,1], q = [1,1,2]',
                             'output': 'false',
                             'explanation': None}],
               'submissionTemplates': {'python': '# LeetCode provides TreeNode with val, left, and '
                                                 'right fields.\n'
                                                 'class Solution:\n'
                                                 '    def isSameTree(self, p: TreeNode | None, q: '
                                                 'TreeNode | None) -> bool:\n'
                                                 '        pass',
                                       'java': '// LeetCode provides TreeNode with val, left, and right '
                                               'fields.\n'
                                               'class Solution {\n'
                                               '    public boolean isSameTree(TreeNode p, TreeNode q) '
                                               '{\n'
                                               '\n'
                                               '    }\n'
                                               '}',
                                       'javascript': '// LeetCode provides TreeNode with val, left, and '
                                                     'right fields.\n'
                                                     'var isSameTree = function(p, q) {\n'
                                                     '\n'
                                                     '};',
                                       'cpp': '// LeetCode provides TreeNode with val, left, and right '
                                              'fields.\n'
                                              'class Solution {\n'
                                              'public:\n'
                                              '    bool isSameTree(TreeNode* p, TreeNode* q) {\n'
                                              '\n'
                                              '    }\n'
                                              '};'}},
 'diameter-of-binary-tree': {'title': 'Diameter of Binary Tree',
                             'difficulty': 'Easy',
                             'leetcodeNumber': 543,
                             'constraints': ['The number of nodes in the tree is in the range [1, '
                                             '10^4].',
                                             '-100 <= Node.val <= 100'],
                             'examples': [{'input': 'root = [1,2,3,4,5]',
                                           'output': '3',
                                           'explanation': 'A longest route runs from node 4 or 5 '
                                                          'through node 2 and node 1 to node 3, '
                                                          'crossing three edges.'},
                                          {'input': 'root = [1,2]', 'output': '1', 'explanation': None}],
                             'submissionTemplates': {'python': '# LeetCode provides TreeNode with val, '
                                                               'left, and right fields.\n'
                                                               'class Solution:\n'
                                                               '    def diameterOfBinaryTree(self, '
                                                               'root: Optional[TreeNode]) -> int:\n'
                                                               '        pass',
                                                     'java': '// LeetCode provides TreeNode with val, '
                                                             'left, and right fields.\n'
                                                             'class Solution {\n'
                                                             '    public int '
                                                             'diameterOfBinaryTree(TreeNode root) {\n'
                                                             '\n'
                                                             '    }\n'
                                                             '}',
                                                     'javascript': '// LeetCode provides TreeNode with '
                                                                   'val, left, and right fields.\n'
                                                                   'var diameterOfBinaryTree = '
                                                                   'function(root) {\n'
                                                                   '\n'
                                                                   '};',
                                                     'cpp': '// LeetCode provides TreeNode with val, '
                                                            'left, and right fields.\n'
                                                            'class Solution {\n'
                                                            'public:\n'
                                                            '    int diameterOfBinaryTree(TreeNode* '
                                                            'root) {\n'
                                                            '\n'
                                                            '    }\n'
                                                            '};'}},
 'balanced-binary-tree': {'title': 'Balanced Binary Tree',
                          'difficulty': 'Easy',
                          'leetcodeNumber': 110,
                          'constraints': ['The number of nodes in the tree is in the range [0, 5000].',
                                          '-10^4 <= Node.val <= 10^4'],
                          'examples': [{'input': 'root = [3,9,20,null,null,15,7]',
                                        'output': 'true',
                                        'explanation': None},
                                       {'input': 'root = [1,2,2,3,3,null,null,4,4]',
                                        'output': 'false',
                                        'explanation': None},
                                       {'input': 'root = []', 'output': 'true', 'explanation': None}],
                          'submissionTemplates': {'python': '# LeetCode provides TreeNode with val, '
                                                            'left, and right fields.\n'
                                                            'class Solution:\n'
                                                            '    def isBalanced(self, root: TreeNode | '
                                                            'None) -> bool:\n'
                                                            '        pass',
                                                  'java': '// LeetCode provides TreeNode with val, '
                                                          'left, and right fields.\n'
                                                          'class Solution {\n'
                                                          '    public boolean isBalanced(TreeNode root) '
                                                          '{\n'
                                                          '\n'
                                                          '    }\n'
                                                          '}',
                                                  'javascript': '// LeetCode provides TreeNode with '
                                                                'val, left, and right fields.\n'
                                                                'var isBalanced = function(root) {\n'
                                                                '\n'
                                                                '};',
                                                  'cpp': '// LeetCode provides TreeNode with val, left, '
                                                         'and right fields.\n'
                                                         'class Solution {\n'
                                                         'public:\n'
                                                         '    bool isBalanced(TreeNode* root) {\n'
                                                         '\n'
                                                         '    }\n'
                                                         '};'}},
 'rotting-oranges': {'title': 'Rotting Oranges',
                     'difficulty': 'Medium',
                     'leetcodeNumber': 994,
                     'constraints': ['m == grid.length',
                                     'n == grid[i].length',
                                     '1 <= m, n <= 10',
                                     'grid[i][j] is 0, 1, or 2.'],
                     'examples': [{'input': 'grid = [[2,1,1],[1,1,0],[0,1,1]]',
                                   'output': '4',
                                   'explanation': None},
                                  {'input': 'grid = [[2,1,1],[0,1,1],[1,0,1]]',
                                   'output': '-1',
                                   'explanation': 'The fresh orange at row 2, column 0 is cut off from '
                                                  'all rotten cells under four-directional spread.'},
                                  {'input': 'grid = [[0,2]]',
                                   'output': '0',
                                   'explanation': 'With no fresh orange at the start, zero minutes are '
                                                  'needed.'}],
                     'submissionTemplates': {'python': 'class Solution:\n'
                                                       '    def orangesRotting(self, grid: '
                                                       'list[list[int]]) -> int:\n'
                                                       '        pass',
                                             'java': 'class Solution {\n'
                                                     '    public int orangesRotting(int[][] grid) {\n'
                                                     '\n'
                                                     '    }\n'
                                                     '}',
                                             'javascript': 'var orangesRotting = function(grid) {\n\n};',
                                             'cpp': 'class Solution {\n'
                                                    'public:\n'
                                                    '    int orangesRotting(vector<vector<int>>& grid) '
                                                    '{\n'
                                                    '\n'
                                                    '    }\n'
                                                    '};'}},
 'house-robber': {'title': 'House Robber',
                  'difficulty': 'Medium',
                  'leetcodeNumber': 198,
                  'constraints': ['1 <= nums.length <= 100', '0 <= nums[i] <= 400'],
                  'examples': [{'input': 'nums = [1,2,3,1]',
                                'output': '4',
                                'explanation': 'Taking the first and third houses yields 1 + 3 = 4 '
                                               'without adjacent choices.'},
                               {'input': 'nums = [2,7,9,3,1]',
                                'output': '12',
                                'explanation': 'Taking houses 1, 3, and 5 yields 2 + 9 + 1 = 12.'}],
                  'submissionTemplates': {'python': 'class Solution:\n'
                                                    '    def rob(self, nums: list[int]) -> int:\n'
                                                    '        pass',
                                          'java': 'class Solution {\n'
                                                  '    public int rob(int[] nums) {\n'
                                                  '\n'
                                                  '    }\n'
                                                  '}',
                                          'javascript': 'var rob = function(nums) {\n\n};',
                                          'cpp': 'class Solution {\n'
                                                 'public:\n'
                                                 '    int rob(vector<int>& nums) {\n'
                                                 '\n'
                                                 '    }\n'
                                                 '};'}},
 'coin-change': {'title': 'Coin Change',
                 'difficulty': 'Medium',
                 'leetcodeNumber': 322,
                 'constraints': ['1 <= coins.length <= 12',
                                 '1 <= coins[i] <= 2^31 - 1',
                                 '0 <= amount <= 10^4'],
                 'examples': [{'input': 'coins = [1,2,5], amount = 11',
                               'output': '3',
                               'explanation': 'Two 5-value coins and one 1-value coin make 11 using '
                                              'three coins.'},
                              {'input': 'coins = [2], amount = 3', 'output': '-1', 'explanation': None},
                              {'input': 'coins = [1], amount = 0', 'output': '0', 'explanation': None}],
                 'submissionTemplates': {'python': 'class Solution:\n'
                                                   '    def coinChange(self, coins: list[int], amount: '
                                                   'int) -> int:\n'
                                                   '        pass',
                                         'java': 'class Solution {\n'
                                                 '    public int coinChange(int[] coins, int amount) {\n'
                                                 '\n'
                                                 '    }\n'
                                                 '}',
                                         'javascript': 'var coinChange = function(coins, amount) {\n'
                                                       '\n'
                                                       '};',
                                         'cpp': 'class Solution {\n'
                                                'public:\n'
                                                '    int coinChange(vector<int>& coins, int amount) {\n'
                                                '\n'
                                                '    }\n'
                                                '};'}}}
