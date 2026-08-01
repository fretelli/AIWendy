import { redirect } from "next/navigation";

export default function Page() { redirect("/agent/market?tab=rates&period=1Y"); }
