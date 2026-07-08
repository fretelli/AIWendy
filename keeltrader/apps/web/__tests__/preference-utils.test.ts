import {
  joinTags,
  normalizeCustomKeywords,
  parseKeywordInput,
  splitTags,
} from "@/components/research/hub/panel-components/preference-utils";

describe("preference-utils", () => {
  it("splits and deduplicates mixed tag separators", () => {
    expect(splitTags("消费、AI, 出海；AI\n医药")).toEqual(["消费", "AI", "出海", "医药"]);
  });

  it("parses keyword drafts from punctuation and whitespace", () => {
    expect(parseKeywordInput("估值 现金流；品牌、出海")).toEqual(["估值", "现金流", "品牌", "出海"]);
  });

  it("joins trimmed unique tags with Chinese separators", () => {
    expect(joinTags([" 消费 ", "AI", "消费", ""])).toBe("消费、AI");
  });

  it("rejects invalid custom keywords", () => {
    expect(normalizeCustomKeywords(["https://example.com"]).error).toBe("自定义关注点不能包含链接或联系方式");
    expect(normalizeCustomKeywords(["111111"]).error).toBe("自定义关注点请填写文字内容");
    expect(normalizeCustomKeywords(["aaaaaa"]).error).toBe("请填写真实关注点");
  });
});
