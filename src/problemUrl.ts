export type ProblemPageMatch =
  | {
      isSupported: true;
      slug: string;
      url: string;
    }
  | {
      isSupported: false;
    };

export function parseLeetCodeProblemUrl(rawUrl?: string): ProblemPageMatch {
  if (!rawUrl) {
    return { isSupported: false };
  }

  try {
    const url = new URL(rawUrl);
    const [problemsSegment, slug] = url.pathname
      .split("/")
      .filter(Boolean);

    if (
      url.protocol !== "https:" ||
      url.hostname !== "leetcode.com" ||
      problemsSegment !== "problems" ||
      !slug
    ) {
      return { isSupported: false };
    }

    return {
      isSupported: true,
      slug,
      url: url.toString()
    };
  } catch {
    return { isSupported: false };
  }
}

export function getProblemDisplayTitle(slug: string, tabTitle?: string) {
  const normalizedTabTitle = tabTitle?.replace(/\s+-\s+LeetCode\s*$/i, "").trim();

  if (normalizedTabTitle && isUsableProblemTitle(normalizedTabTitle)) {
    return normalizedTabTitle;
  }

  return slug
    .split("-")
    .filter(Boolean)
    .map(formatTitleWord)
    .join(" ");
}

function isUsableProblemTitle(title: string) {
  const lowerTitle = title.toLowerCase();

  return (
    lowerTitle !== "leetcode" &&
    !lowerTitle.startsWith("http") &&
    !lowerTitle.includes("leetcode.com/problems/")
  );
}

function formatTitleWord(word: string, index: number) {
  const lowercaseWord = word.toLowerCase();
  const smallWords = new Set(["a", "an", "and", "in", "of", "or", "the", "to"]);
  const romanNumerals = new Set(["i", "ii", "iii", "iv", "v"]);

  if (romanNumerals.has(lowercaseWord)) {
    return lowercaseWord.toUpperCase();
  }

  if (index > 0 && smallWords.has(lowercaseWord)) {
    return lowercaseWord;
  }

  return lowercaseWord.charAt(0).toUpperCase() + lowercaseWord.slice(1);
}
