import { describe, expect, it } from "vitest";
import { getProblemDisplayTitle } from "../src/problemUrl";

describe("problem display title", () => {
  it("does not use the previous problem's title with a new slug", () => {
    expect(getProblemDisplayTitle(
      "add-two-numbers", "Lowest Common Ancestor of a Binary Search Tree - LeetCode"
    )).toBe("Add Two Numbers");
  });

  it("keeps a matching LeetCode title, including its problem number", () => {
    expect(getProblemDisplayTitle("add-two-numbers", "2. Add Two Numbers - LeetCode"))
      .toBe("2. Add Two Numbers");
  });
});
