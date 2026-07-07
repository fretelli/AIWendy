import { BookOpen, Building2, Gift, History, MessageSquare, Settings2, Ticket } from "lucide-react";

import { type PointsMallItem } from "@/lib/research-api";

export const FALLBACK_MALL_ITEMS: PointsMallItem[] = [
  {
    code: "book_blind_watchmaker",
    name: "《盲眼钟表匠》",
    subtitle: "[英] 理查德·道金斯，中译版。",
    category: "book",
    points_cost: 20000,
    stock: 1,
    cover_theme: "macro",
    cover_image: "/static/book-blind-watchmaker.png",
    description: "从进化论视角理解复杂生命如何在自然选择中形成。",
    can_redeem: false,
  },
  {
    code: "book_zebra_ulcers",
    name: "《斑马为什么不得胃溃疡》",
    subtitle: "[美] 罗伯特·萨波尔斯基，中译版。",
    category: "book",
    points_cost: 20000,
    stock: 1,
    cover_theme: "value",
    cover_image: "/static/book-zebra-ulcers.png",
    description: "用通俗科学解释压力、身体反应与现代生活的长期损耗。",
    can_redeem: false,
  },
  {
    code: "book_namiya",
    name: "《解忧杂货店》",
    subtitle: "[日] 东野圭吾，中译版。",
    category: "book",
    points_cost: 20000,
    stock: 1,
    cover_theme: "risk",
    cover_image: "/static/book-namiya.png",
    description: "以温柔叙事串起咨询来信、人生选择与迟来的回应。",
    can_redeem: false,
  },
];

export const MODULES = [
  { value: "reports", label: "推荐研报", icon: BookOpen },
  { value: "digests", label: "往期期刊", icon: History },
  { value: "funds", label: "机构图鉴", icon: Building2 },
  { value: "mall", label: "积分商城", icon: Gift },
  { value: "membership", label: "权益中心", icon: Ticket },
  { value: "preferences", label: "兴趣设置", icon: Settings2 },
  { value: "feedback", label: "意见反馈", icon: MessageSquare },
] as const;

export const BLOCKED_KEYWORDS = ["test", "testing", "asdf", "qwer", "null", "none", "unknown", "测试", "无", "不知道", "随便"];

export const PROMPT_TEMPLATES = [
  {
    id: "concise",
    title: "更简洁",
    description: "摘要更短，直接说重点，少空话。",
    prompt: "请用更简洁的中文写摘要，直接说重点，少空话，不要重复标题。",
  },
  {
    id: "plain",
    title: "更通俗",
    description: "像解释给非专业用户，少术语。",
    prompt: "请用更通俗的中文写摘要，像解释给非专业用户一样，少用术语，表达清楚。",
  },
  {
    id: "structured",
    title: "更结构化",
    description: "先结论，再重点，再补充说明。",
    prompt: "请把摘要写得更结构化：先说结论，再列重点，最后补充说明，层次清楚。",
  },
  {
    id: "insight",
    title: "更关注启发",
    description: "更强调对行业、品牌、经营动作的实际启发。",
    prompt: "请更关注这篇内容对行业、品牌和经营动作的实际启发，少写空泛判断，多写具体意义。",
  },
] as const;
