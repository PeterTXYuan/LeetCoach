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
