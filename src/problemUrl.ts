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
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
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
